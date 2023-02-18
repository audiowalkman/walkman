from __future__ import annotations

import abc
import copy
import functools
import importlib
import inspect
import pkgutil
import typing
import warnings

import pyo

import walkman


__all__ = (
    "ModuleInput",
    "Catch",
    "AutoSetup",
    "Module",
    "ModuleWithFader",
    "ModuleContainer",
)


def override_default_kwargs(method_to_wrap: typing.Callable) -> typing.Callable:
    def wrapper(self, **kwargs):
        default_dict = copy.deepcopy(self.default_dict)
        default_dict.update(kwargs)
        return method_to_wrap(self, **default_dict)

    return wrapper


class ModuleInput(abc.ABC):
    """Allocate an Module object as an input of another Module

    :param implicit: If implicit is `True` a module is activated if any module
        in it's input or output chain is activated during the given cue. If
        implicit is `False` a module is only activated if it is explicitly
        activated in a given cue.
    :type implicit: bool
    """

    def __init__(self, implicit: bool = True):
        self.implicit = implicit

    def get_replication_key(
        self,
        parent: typing.Optional[Module] = None,
        module_input_name: str = "",
    ) -> str:
        # So we can use the syntax:
        #   [configure.module.sine.example]
        #
        #   [configure.module.value.sine_example_child_frequency]
        #   value = 440
        if parent:
            return f"{str(parent).replace('.', '_')}_child_{module_input_name}"
        else:
            return ""

    @abc.abstractmethod
    def __call__(
        self,
        module_container: ModuleContainer,
        parent: typing.Optional[Module] = None,
        module_input_name: str = "",
    ) -> Module:
        ...


class InvalidModuleInstanceNameWarning(RuntimeWarning):
    def __init__(self, module_instance_name: str, parent: typing.Optional[Module]):
        super().__init__(
            f"WALKMAN couldn't find the module '{module_instance_name}' for "
            f"the parent module '{str(parent)}'."
        )


class Catch(ModuleInput):
    def __init__(self, module_instance_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.module_instance_name = module_instance_name

    def __call__(
        self,
        module_container: ModuleContainer,
        parent: typing.Optional[Module] = None,
        module_input_name: str = "",
    ) -> Module:

        if self.module_instance_name == str(parent):
            raise ModuleHasItselfAsAnInputError(self.module_instance_name)

        try:
            return module_container.get_module_by_name(self.module_instance_name)
        except (KeyError, InvalidModuleInstanceNameError):
            warnings.warn(
                InvalidModuleInstanceNameWarning(self.module_instance_name, parent)
            )
            return module_container.get_module_by_name(
                walkman.constants.EMPTY_MODULE_INSTANCE_NAME
            )

    def __str__(self) -> str:
        return f"{type(self).__name__}('{self.module_instance_name}')"


class AutoSetup(ModuleInput):
    def __init__(
        self,
        module_class: typing.Type[Module],
        module_kwargs: dict = {},
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.module_class = module_class
        self.module_kwargs = module_kwargs

    def __call__(
        self,
        module_container: ModuleContainer,
        parent: typing.Optional[Module] = None,
        module_input_name: str = "",
    ) -> Module:
        module_kwargs = dict(self.module_kwargs)
        try:
            replication_key = module_kwargs["replication_key"]
        except KeyError:
            module_kwargs[
                "replication_key"
            ] = replication_key = self.get_replication_key(parent, module_input_name)
        finally:
            module_instance_name = (
                f"{self.module_class.get_class_name()}.{replication_key}"
            )

            if module_instance_name == str(parent):
                raise ModuleHasItselfAsAnInputError(module_instance_name)

            try:
                return module_container.get_module_by_name(module_instance_name)
            except (KeyError, InvalidModuleInstanceNameError):
                pass

        module = self.module_class(**module_kwargs)
        module_instance_dict = {id(module): module}
        module_name = module.get_class_name()
        try:
            module_container[module_name].update(module_instance_dict)
        except KeyError:
            module_container.update({module_name: module_instance_dict})
        return module


class IgnoredInitializationArgumentsWarning(RuntimeWarning):
    def __init__(self, module: Module, ignored_kwargs: dict):
        super().__init__(
            "The following unexpected key word arguments "
            f"which were given to '{str(module)}' have "
            f"been ignored by WALKMAN: {ignored_kwargs}"
        )


class MissingInitializationArgumentsWarning(RuntimeWarning):
    def __init__(self, module: Module, error_string: str):
        super().__init__(
            f"The module {module} missed initialization arguments "
            "(which need to be provided with either the [configure.module.name.default_dict]"
            " syntax or with the [cue.cue_name.module.name] syntax)."
            " WALKMAN skipped the initialization of the given module."
            f" The original error is:\n{error_string}."
        )


class InvalidModuleInputError(Exception):
    """Raise for invalid audio input argument of a module."""


class ModuleHasItselfAsAnInputError(InvalidModuleInputError):
    def __init__(self, module_instance_name: str):
        super().__init__(
            f"Module '{module_instance_name}' has invalid module "
            f"input '{module_instance_name}'! A module can not have "
            "itself as an input."
        )


class Module(
    walkman.PlayMixin,
    walkman.JumpToMixin,
    walkman.NamedMixin,
    walkman.CloseMixin,
    walkman.PyoObjectMixin,
):
    def __init__(
        self,
        replication_key: str = "",
        send_to_physical_output: bool = False,
        auto_stop: bool = True,
        module_input_dict: dict[str, ModuleInput] = dict([]),
        default_dict: dict[str, typing.Any] = dict([]),
    ):
        self.replication_key = replication_key
        self.send_to_physical_output = send_to_physical_output
        self.auto_stop = auto_stop
        self.output_module_set = set([])
        self.module_input_dict = module_input_dict
        self.default_dict = default_dict
        self.internal_pyo_object_list = []

    def __new__(cls, *args, **kwargs):
        module = super().__new__(cls)
        module.__init__(*args, **kwargs)
        switch = walkman.PyoObjectMixinSwitch(module)
        return switch

    def __init_subclass__(cls, **module_input_dict: ModuleInput):
        try:
            cls.default_module_input_dict = dict(
                cls.default_module_input_dict, **module_input_dict
            )
        except AttributeError:
            cls.default_module_input_dict = module_input_dict
            is_subclass = False
        else:
            is_subclass = True

        if not is_subclass:
            user_defined_init = cls.__init__

            def __init__(self, **kwargs):
                module_input_dict = {}
                for (
                    module_input_name,
                    default_module_input,
                ) in self.default_module_input_dict.items():
                    module_input = default_module_input
                    try:
                        module_instance_name = kwargs[module_input_name]
                    except KeyError:
                        pass
                    else:
                        module_input = Catch(
                            module_instance_name, implicit=module_input.implicit
                        )
                        del kwargs[module_input_name]
                    finally:
                        module_input_dict.update({module_input_name: module_input})

                user_defined_init(self, module_input_dict=module_input_dict, **kwargs)

            cls.__init__ = __init__

    def __str__(self) -> str:
        return f"{self.get_class_name()}.{self.replication_key}"

    def __repr__(self) -> str:
        return str(self)

    # ################## PRIVATE METHODS     ################## #

    def _play_without_fader(self, duration: float = 0, delay: float = 0):
        self.pyo_object.play(dur=duration, delay=delay)
        for internal_pyo_object in self.internal_pyo_object_list:
            internal_pyo_object.play(dur=duration, delay=delay)

        if self.send_to_physical_output:
            for channel_index, audio_stream in enumerate(self.pyo_object):
                audio_stream.out(channel_index)

    def _play(self, duration: float = 0, delay: float = 0):
        self._play_without_fader(duration, delay)

    def _stop_without_fader(self, wait: float = 0):
        for internal_pyo_object in self.internal_pyo_object_list:
            internal_pyo_object.stop(wait=wait)
        self.pyo_object.stop(wait=wait)

    def _stop(self, wait: float = 0):
        self._stop_without_fader(wait=wait)

    def _initialise(self, **kwargs):
        if kwargs:
            warnings.warn(IgnoredInitializationArgumentsWarning(self, kwargs))

    def _setup_pyo_object(self):
        ...

    # ################## PUBLIC METHODS      ################## #

    def setup(self, module_container: ModuleContainer):
        self.assign_module_inputs(module_container)
        self.setup_pyo_object()

    def assign_module_inputs(self, module_container: ModuleContainer):
        if not self.has_assigned_inputs:
            for module_input_name, module_input in self.module_input_dict.items():
                module = module_input(
                    module_container, parent=self, module_input_name=module_input_name
                )
                module.output_module_set.add(self)
                setattr(self, module_input_name, module)

            self._has_assigned_inputs = True

    def setup_pyo_object(self):
        if not self.has_setup_pyo_object:
            self._setup_pyo_object()
            self._has_setup_pyo_object = True

    @override_default_kwargs
    def initialise(
        self,
        **kwargs,
    ) -> tuple[Module, ...]:
        """Function returns tuple of all modules which have been initialised"""

        kwargs, initialised_module_list = self._initialise_syntactic_sugar_0(**kwargs)

        # Parse everything else to actual initialise method.
        try:
            self._initialise(**kwargs)
        except TypeError as error:
            warnings.warn(MissingInitializationArgumentsWarning(self, str(error)))

        # When switching playing cues the 'play' method
        # won't be called. But we have to ensure that the envelopes
        # are running once we start a new cue.
        if self.is_playing:
            self._play_without_fader()

        initialised_module_list.append(self)
        return tuple(initialised_module_list)

    # Tested in 'test_initialise_syntactic_sugar_0'
    def _initialise_syntactic_sugar_0(self, **kwargs) -> tuple[dict, list[Module]]:
        """Allow syntactic sugar to set parameter values.

        If a module has another (maybe auto-generated) module as
        its input, we can set the 'initialise' parameters of the
        input in the following way:

        [cue.CUE_NAME.MODULE_NAME.REPLICATION_KEY.INPUT_NAME]

        so for instance, creating an octave glissando:

        [cue.1.sine.0.frequency]
        value = [[0, 220], [10, 440]]

        This construct also allows the special syntax

        [cue.CUE_NAME.MODULE_NAME.REPLICATION_KEY]
        INPUT_NAME = VALUE

        if the module input is of type "Parameter".
        So for instance:

        [cue.1.sine.0]
        frequency = 110
        """

        # XXX: Can we find a more efficient way for this function?
        # This is called whenever we switch a cue (and is therefore not
        # during initialization time, but performance time, so it can badly
        # effect performance speed).
        initialised_module_list = []
        new_kwargs = {}

        for argument_key, argument_value in kwargs.items():
            try:
                module_instance = self.module_input_dict[argument_key]
            except KeyError:
                new_kwargs.update({argument_key: argument_value})
            else:
                module_instance = getattr(self, argument_key)
                if isinstance(argument_value, dict):
                    module_instance_kwargs = argument_value
                elif isinstance(argument_value, (float, int)) and isinstance(
                    module_instance, walkman.Parameter
                ):
                    module_instance_kwargs = {"value": argument_value}
                else:
                    warnings.warn(
                        f"Found invalid type '{type(argument_value)}' "
                        f"of argument value '{argument_value}' for "
                        f"argument_key '{argument_key}' for input module instance!"
                    )
                    continue

                module_instance.initialise(**module_instance_kwargs)
                initialised_module_list.append(module_instance)

        return new_kwargs, initialised_module_list

    # ################## PUBLIC PROPERTIES  ################## #

    @functools.cached_property
    def pyo_object(self) -> pyo.PyoObject:
        try:
            return self._pyo_object
        except AttributeError:
            # Some modules (for instance 'Value') don't define a 'pyo_object',
            # but only define a property for 'pyo_object_or_float'. Usually
            # other modules should only use them via their
            # 'pyo_object_or_float' attribute, but if another module is badly
            # programmed it may use the other objects 'pyo_object' attribute.
            # This is not extremely dangerous, but still unexpected and should
            # therefore raise a warning.
            #
            # Another option why we end up here, is simply because the (python
            # side) module definition is incomplete. Then we should fix this
            # module.
            warnings.warn(
                f"No '_pyo_object' is defined for module '{self}'. "
                "Fallback to default 'pyo_object' (a signal 'f(x) = 0'). "
                "Did another module call this module via its 'pyo_object' "
                "property? Maybe change this to 'pyo_object_or_float'."
            )
            pyo_object = super().pyo_object
            self.internal_pyo_object_list.append(pyo_object)
            return pyo_object

    @property
    def fade_in_duration(self) -> float:
        return 0

    @property
    def fade_out_duration(self) -> float:
        return 0

    @property
    def has_assigned_inputs(self) -> bool:
        try:
            return self._has_assigned_inputs
        except AttributeError:
            return False

    @property
    def has_setup_pyo_object(self) -> bool:
        try:
            return self._has_setup_pyo_object
        except AttributeError:
            return False

    @property
    def duration(self) -> float:
        return 0

    @functools.cached_property
    def module_input_chain(self) -> tuple[Module, ...]:
        """Get chain of all inputs from left to right (order matters!).

        This returns both input modules: explicit modules
        (e.g. which are only active if explicitly activated via the
        [cue.CUE_NAME.MODULE_NAME.REPLICATION_KEY] syntax) and
        implicit modules (e.g. which are active if they are explicitly
        activated OR/AND if their output is explicitly activated).
        """
        return self._module_input_chain(lambda m: m.module_input_chain)

    @functools.cached_property
    def implicit_module_input_chain(self) -> tuple[Module, ...]:
        """Get chain of implicit inputs from left to right (order matters!).

        This only returns implicit modules (e.g. which are active if their
        output is explicitly activated) and skips explicit modules.
        """
        return self._module_input_chain(
            lambda m: m.implicit_module_input_chain, lambda m: m.implicit
        )

    def _module_input_chain(
        self,
        module_to_module_input_chain: typing.Callable[[Module], tuple[Module, ...]],
        module_input_filter: typing.Callable[[ModuleInput], bool] = lambda m: True,
    ):
        input_module_list = []
        for module_input_name, module_input in self.module_input_dict.items():
            if module_input_filter(module_input):
                input_module = getattr(self, module_input_name).base
                if input_module not in input_module_list:
                    input_module_list.append(input_module)
                for module_instance in reversed(
                    module_to_module_input_chain(input_module)
                ):
                    if module_instance not in input_module_list:
                        input_module_list.append(module_instance)
        return tuple(reversed(input_module_list))

    @functools.cached_property
    def module_output_chain(self) -> tuple[Module, ...]:
        output_module_list = []
        for output_module in self.output_module_set:
            if output_module not in output_module_list:
                output_module_list.append(output_module)
            for module_instance in output_module.implicit_module_chain:
                if (
                    module_instance not in output_module_list
                    and module_instance != self
                ):
                    output_module_list.append(module_instance)
        return tuple(output_module_list)

    @functools.cached_property
    def module_chain(self) -> tuple[Module, ...]:
        module_list = list(self.module_input_chain)
        for module_instance in self.module_output_chain:
            if module_instance not in module_list:
                module_list.append(module_instance)
        return tuple(module_list)

    @functools.cached_property
    def implicit_module_chain(self) -> tuple[Module, ...]:
        module_list = list(self.implicit_module_input_chain)
        for module_instance in self.module_output_chain:
            if module_instance not in module_list:
                module_list.append(module_instance)
        return tuple(module_list)


class ModuleWithFader(Module):
    def __init__(
        self, fade_in_duration: float = 0.1, fade_out_duration: float = 0.2, **kwargs
    ):
        super().__init__(**kwargs)
        self.fade_in_duration = fade_in_duration
        self.fade_out_duration = fade_out_duration

    # ################## ABSTRACT PROPERTIES ################## #

    @abc.abstractproperty
    def _pyo_object(self) -> pyo.PyoObject:
        ...

    # ################## PRIVATE METHODS     ################## #

    def _setup_pyo_object(self):
        self.fader = pyo.Fader(
            fadein=self.fade_in_duration, fadeout=self.fade_out_duration
        )
        # XXX: We need to use a trigger for stopping the fader, because
        # fader objects ignore the 'wait' parameter. Without this trigger
        # the wait parameter wouldn't work.
        self.fader_stopper = pyo.Trig().stop()
        self.fader_stopper_function = pyo.TrigFunc(
            input=self.fader_stopper,
            function=lambda: self.fader.stop() if not self.is_playing else None,
        ).play()

    def _play(self, duration: float = 0, delay: float = 0):
        self.fader.play(dur=duration, delay=delay)
        self._play_without_fader(duration, delay)

    def _stop(self, wait: float = 0):
        self.fader_stopper.play(delay=wait)
        self._stop_without_fader(wait=wait + self.fade_out_duration)

    # ################## PUBLIC PROPERTIES ################## #

    @property
    def fade_in_duration(self) -> float:
        return self._fade_in_duration

    @fade_in_duration.setter
    def fade_in_duration(self, fade_in_duration: float):
        self._fade_in_duration = fade_in_duration

    @property
    def fade_out_duration(self) -> float:
        return self._fade_out_duration

    @fade_out_duration.setter
    def fade_out_duration(self, fade_out_duration: float):
        self._fade_out_duration = fade_out_duration

    @functools.cached_property
    def pyo_object(self) -> pyo.PyoObject:
        pyo_object = self._pyo_object * self.fader
        pyo_object.stop()
        return pyo_object


class InvalidModuleInstanceNameError(Exception):
    def __init__(self, invalid_module_instance_name: str):
        super().__init__(
            f"Found invalid module instance name '{invalid_module_instance_name}'!"
        )


ModuleName = str
ReplicationKey = str
ModuleNameToModuleClassDict = dict[str, typing.Type[Module]]


class UndefinedModuleWarning(Warning):
    def __init__(self, undefined_module_name: str):
        super().__init__(
            f"Found undefined module '{undefined_module_name}'. "
            "WALKMAN ignored given module configurations."
        )


class NoPhysicalOutputWarning(Warning):
    def __init__(self, module_without_output: Module):
        message_list = [
            f"WALKMAN detected module '{str(module_without_output)}' which "
            "has no connection to any other module which is"
            " send to a physical output. This may be the result from "
            f"bad routing. "
        ]
        module_output_chain = [
            str(module) for module in module_without_output.module_output_chain
        ]
        if module_output_chain:
            output_chain = "\n- ".join(module_output_chain)
            message_list.append(f"The given output chain is: \n\n- {output_chain}\n")
        else:
            message_list.append("This module has an empty output chain.")
        super().__init__(" ".join(message_list))


class ConfigureModuleError(TypeError):
    def __init__(
        self,
        replication_key: str,
        module_class: typing.Type[Module],
        module_configuration: dict[str, typing.Any],
        exception_text: str,
    ):
        super().__init__(
            f"Found invalid module configuration for module "
            f"'{module_class.get_class_name()}.{replication_key}':\n\n"
            f"{module_configuration}\n"
            "(Original TypeError message:\n"
            f"{exception_text}"
        )


class ModuleContainer(
    dict[ModuleName, dict[ReplicationKey, Module]], walkman.CloseMixin
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if "empty" not in self:
            self.update({"empty": {}})

        self["empty"].update(
            {
                walkman.constants.EMPTY_MODULE_INSTANCE_NAME.split(".")[
                    1
                ]: walkman.Empty()
            }
        )
        for module in self.module_tuple:
            self.prepare_module(module)
            module._stop_without_fader()

        for module in self.module_tuple:
            if not (is_send_to_physical_output := module.send_to_physical_output):
                for output_module in module.module_output_chain:
                    if (
                        is_send_to_physical_output := output_module.send_to_physical_output
                    ):
                        break
                if not is_send_to_physical_output and not isinstance(
                    module, walkman.Empty
                ):
                    warnings.warn(NoPhysicalOutputWarning(module))

    def prepare_module(self, module_instance: Module):
        def assign_module_inputs(module_instance: Module):
            for module_input_name in module_instance.module_input_dict.keys():
                local_module_instance = getattr(module_instance, module_input_name)
                local_module_instance.assign_module_inputs(self)
                assign_module_inputs(local_module_instance)

        def setup_module_inputs_pyo_object(module_instance: Module):
            for input_module_instance in module_instance.module_input_chain:
                setup_module_inputs_pyo_object(input_module_instance)
                input_module_instance.setup_pyo_object()

        module_instance.assign_module_inputs(self)

        assign_module_inputs(module_instance)
        setup_module_inputs_pyo_object(module_instance)

        module_instance.setup_pyo_object()

    @staticmethod
    def get_module_name_to_module_class_dict() -> ModuleNameToModuleClassDict:
        try:
            namespace_package = __import__(walkman.constants.MODULE_PACKAGE_NAME)
        except ModuleNotFoundError:
            module_list = []
        else:
            module_list = list(
                importlib.import_module(module_info.name)
                for module_info in pkgutil.iter_modules(
                    namespace_package.__path__, namespace_package.__name__ + "."
                )
            )
        module_list.append(importlib.import_module("walkman.modules.buildins"))
        module_name_to_module_class_dict = {}
        for module in module_list:
            for _, python_class in inspect.getmembers(module, inspect.isclass):
                if Module in inspect.getmro(python_class):
                    module_name_to_module_class_dict.update(
                        {python_class.get_class_name(): python_class}
                    )
        return module_name_to_module_class_dict

    @classmethod
    def from_module_configuration(
        cls,
        module_name_to_replication_configuration_dict: dict[
            str, dict[str, dict[str, typing.Any]]
        ],
        module_name_to_module_class_dict: typing.Optional[
            ModuleNameToModuleClassDict
        ] = None,
    ) -> ModuleContainer:
        if module_name_to_module_class_dict is None:
            module_name_to_module_class_dict = (
                cls.get_module_name_to_module_class_dict()
            )

        # XXX: We have to iterate over 'module_name_to_module_class_dict'
        # instead of iterating over module_name_to_replication_configuration_dict,
        # because of syntactic sugar [configure.MODULE_NAME.REPLICATION_KEY.INPUT_NAME]
        module_name_to_module_container = {}
        for module_name, module_class in module_name_to_module_class_dict.items():
            try:
                replication_key_to_module_configuration_dict = (
                    module_name_to_replication_configuration_dict[module_name]
                )
            except KeyError:
                continue
            # For debugging (see below)
            del module_name_to_replication_configuration_dict[module_name]
            module_dict = {}
            for (
                replication_key,
                module_configuration,
            ) in replication_key_to_module_configuration_dict.items():
                try:
                    module = module_class(
                        replication_key=replication_key, **module_configuration
                    )
                except TypeError as type_error:
                    raise ConfigureModuleError(
                        replication_key,
                        module_class,
                        module_configuration,
                        str(type_error),
                    )
                module_dict[replication_key] = module
            if module_dict:
                module_name_to_module_container.update({module_name: module_dict})

        for module_name in module_name_to_replication_configuration_dict:
            warnings.warn(UndefinedModuleWarning(module_name))

        return cls(module_name_to_module_container)

    def close(self):
        for module in self.module_tuple:
            module.close()

    @property
    def module_tuple(self) -> tuple[walkman.Module, ...]:
        module_list: list[walkman.Module] = []
        for module_dict in self.values():
            module_list.extend(module_dict.values())
        return tuple(module_list)

    def get_module_by_name(self, module_instance_name: str) -> Module:
        try:
            pointer = module_instance_name.split(".")
            # We either allow the syntax "MODULE_NAME.REPLICATION_KEY" or
            # "MODULE_NAME.REPLICATION_KEY.PYO_OBJECT_INDEX".
            if len(pointer) == 2:
                module_name, replication_key = pointer
                pyo_object_index = 0
            else:
                module_name, replication_key, pyo_object_index = pointer
            pyo_object_index = int(pyo_object_index)
        except (AttributeError, ValueError):
            raise InvalidModuleInstanceNameError(module_instance_name)
        else:
            return self[module_name][replication_key].switch(pyo_object_index)
