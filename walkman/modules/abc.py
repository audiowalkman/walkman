from __future__ import annotations

import abc
import copy
import dataclasses
import functools
import importlib
import inspect
import pkgutil
import typing

import pyo

import walkman


__all__ = ("ModuleInput", "Catch", "AutoSetup", "Module", "ModuleContainer")


def override_default_kwargs(method_to_wrap: typing.Callable) -> typing.Callable:
    def wrapper(self, **kwargs):
        default_dict = copy.deepcopy(self.default_dict)
        default_dict.update(kwargs)
        return method_to_wrap(self, **default_dict)

    return wrapper


class ModuleInput(abc.ABC):
    """Allocate an Module object as an input of another Module"""

    def __init__(self, relevance: bool = True):
        self.relevance = relevance

    @abc.abstractmethod
    def __call__(self, module_container: ModuleContainer) -> Module:
        ...


class Catch(ModuleInput):
    def __init__(self, module_instance_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.module_instance_name = module_instance_name

    def __call__(self, module_container: ModuleContainer) -> Module:
        try:
            return module_container.get_module_by_name(self.module_instance_name)
        except (KeyError, InvalidModuleInstanceNameError):
            return module_container.get_module_by_name(
                walkman.constants.EMPTY_MODULE_INSTANCE_NAME
            )


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

    def __call__(self, module_container: ModuleContainer) -> Module:
        module = self.module_class(**self.module_kwargs)
        module_instance_dict = {id(module): module}
        module_name = module.get_class_name()
        try:
            module_container[module_name].update(module_instance_dict)
        except KeyError:
            module_container.update({module_name: module_instance_dict})
        return module


@dataclasses.dataclass()
class Module(
    walkman.PlayMixin,
    walkman.JumpToMixin,
    walkman.NamedMixin,
    walkman.CloseMixin,
    walkman.PyoObjectMixin,
):
    send_to_physical_output: bool = False
    auto_stop: bool = True
    fade_in_duration: float = 0.001
    fade_out_duration: float = 0.001
    output_module_set: typing.Set[Module] = dataclasses.field(
        default_factory=lambda: set([])
    )
    module_input_dict: typing.Dict[str, ModuleInput] = dataclasses.field(
        default_factory=lambda: {}
    )
    default_dict: typing.Dict[str, typing.Any] = dataclasses.field(
        default_factory=lambda: {}
    )
    internal_pyo_object_list: typing.List[pyo.PyoObject] = dataclasses.field(
        default_factory=lambda: []
    )

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
                            module_instance_name, relevance=module_input.relevance
                        )
                        del kwargs[module_input_name]
                    finally:
                        module_input_dict.update({module_input_name: module_input})

                user_defined_init(self, module_input_dict=module_input_dict, **kwargs)

            cls.__init__ = __init__

    def __hash__(self) -> int:
        # XXX: This method is overridden by dataclasses and
        # has to be manually added again.
        return walkman.NamedMixin.__hash__(self)

    # ################## ABSTRACT PROPERTIES ################## #

    @abc.abstractproperty
    def _pyo_object(self) -> pyo.PyoObject:
        ...

    # ################## ABSTRACT METHODS    ################## #

    def _initialise(self, **_):
        ...

    # ################## PRIVATE METHODS     ################## #

    def _play(self, duration: float = 0, delay: float = 0):
        # self.fader.play(dur=duration, delay=delay)
        self.fader.play(dur=duration, delay=delay)
        self.pyo_object.play(dur=duration, delay=delay)
        for internal_pyo_object in self.internal_pyo_object_list:
            internal_pyo_object.play(dur=duration, delay=delay)

        if self.send_to_physical_output:
            for channel_index, audio_stream in enumerate(self.pyo_object):
                audio_stream.out(channel_index)

    def _stop(self, wait: float = 0):
        self.fader_stopper.play(delay=wait)
        wait += self.fade_out_duration
        for internal_pyo_object in self.internal_pyo_object_list:
            internal_pyo_object.stop(wait=wait)
        self.pyo_object.stop(wait=wait)

    # ################## PUBLIC METHODS      ################## #

    def setup(self, module_container: ModuleContainer):
        self.assign_module_inputs(module_container)
        self.setup_pyo_object()

    def assign_module_inputs(self, module_container: ModuleContainer):
        for module_input_name, module_input in self.module_input_dict.items():
            module = module_input(module_container)
            module.output_module_set.add(self)
            setattr(self, module_input_name, module)

    def setup_pyo_object(self):
        self.fader = pyo.Fader(
            fadein=self.fade_in_duration, fadeout=self.fade_out_duration
        )
        # XXX: We need to use a trigger for stopping the fader, because
        # fader objects ignore the 'wait' parameter. Without this trigger
        # the wait parameter wouldn't work.
        self.fader_stopper = pyo.Trig().stop()
        self.fader_stopper_function = pyo.TrigFunc(
            input=self.fader_stopper, function=self.fader.stop
        ).play()

    @override_default_kwargs
    def initialise(
        self,
        **kwargs,
    ):
        print("INITIALISE")
        # Parse everything else to actual initialise method
        self._initialise(**kwargs)

    # ################## PUBLIC PROPERTIES  ################## #

    @property
    def duration(self) -> float:
        return 0

    @functools.cached_property
    def pyo_object(self) -> pyo.PyoObject:
        pyo_object = self._pyo_object * self.fader
        pyo_object.stop()
        return pyo_object

    @functools.cached_property
    def module_input_chain(self) -> typing.Tuple[Module, ...]:
        """Get chain of inputs from left to right (order matters!)"""

        input_module_list = []
        for module_input_name in self.module_input_dict.keys():
            input_module = getattr(self, module_input_name)
            input_module_list.append(input_module)
            input_module_list.extend(input_module.module_input_chain)
        return tuple(reversed(input_module_list))

    @functools.cached_property
    def relevant_module_input_chain(self) -> typing.Tuple[Module, ...]:
        """Get chain of relevant inputs from left to right (order matters!)"""

        input_module_list = []
        for module_input_name, module_input in self.module_input_dict.items():
            if module_input.relevance:
                input_module = getattr(self, module_input_name)
                if input_module not in input_module_list:
                    input_module_list.append(input_module)
                for module_instance in input_module.relevant_module_input_chain:
                    if module_instance not in input_module_list:
                        input_module_list.append(module_instance)
        return tuple(reversed(input_module_list))

    @functools.cached_property
    def module_output_chain(self) -> typing.Tuple[Module, ...]:
        output_module_list = []
        for output_module in self.output_module_set:
            if output_module not in output_module_list:
                output_module_list.append(output_module)
            for module_instance in output_module.relevant_module_chain:
                if (
                    module_instance not in output_module_list
                    and module_instance != self
                ):
                    output_module_list.append(module_instance)
        return tuple(output_module_list)

    @functools.cached_property
    def module_chain(self) -> typing.Tuple[Module, ...]:
        module_list = list(self.module_input_chain)
        for module_instance in self.module_output_chain:
            if module_instance not in module_list:
                module_list.append(module_instance)
        return tuple(module_list)

    @functools.cached_property
    def relevant_module_chain(self) -> typing.Tuple[Module, ...]:
        module_list = list(self.relevant_module_input_chain)
        for module_instance in self.module_output_chain:
            if module_instance not in module_list:
                module_list.append(module_instance)
        return tuple(module_list)


class InvalidModuleInstanceNameError(Exception):
    def __init__(self, invalid_module_instance_name: str):
        super().__init__(
            f"Found invalid module instance name '{invalid_module_instance_name}'!"
        )


ModuleName = str
ReplicationKey = str
ModuleNameToModuleClassDict = typing.Dict[str, typing.Type[Module]]


class ModuleContainer(
    typing.Dict[ModuleName, typing.Dict[ReplicationKey, Module]], walkman.CloseMixin
):
    @staticmethod
    def get_module_name_to_module_class_dict() -> ModuleNameToModuleClassDict:
        namespace_package = __import__(walkman.constants.MODULE_PACKAGE_NAME)
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
                        {python_class.get_name(): python_class}
                    )
        return module_name_to_module_class_dict

    @classmethod
    def from_module_configuration(
        cls,
        module_name_to_replication_configuration_dict: typing.Dict[
            str, typing.Dict[str, typing.Dict[str, typing.Any]]
        ],
        module_name_to_module_class_dict: typing.Optional[
            ModuleNameToModuleClassDict
        ] = None,
    ) -> ModuleContainer:
        if module_name_to_module_class_dict is None:
            module_name_to_module_class_dict = (
                cls.get_module_name_to_module_class_dict()
            )

        module_name_to_module_container = {}
        for module_name, module_class in module_name_to_module_class_dict.items():
            try:
                replication_key_to_module_configuration_dict = (
                    module_name_to_replication_configuration_dict[module_name]
                )
            except KeyError:
                replication_key_to_module_configuration_dict = {}
            module_dict = {}
            for (
                replication_key,
                module_configuration,
            ) in replication_key_to_module_configuration_dict.items():
                module = module_class(**module_configuration)
                module_dict[replication_key] = module
            module_name_to_module_container.update({module_name: module_dict})
        return cls(module_name_to_module_container)

    def close(self):
        for module in self.module_tuple:
            module.close()

    @property
    def module_tuple(self) -> typing.Tuple[walkman.Module, ...]:
        module_list: typing.List[walkman.Module] = []
        for module_tuple in self.values():
            module_list.extend(module_tuple)
        return tuple(module_list)

    def get_module_by_name(self, module_instance_name: str) -> Module:
        try:
            module_name, replication_key = module_instance_name.split(".")
        except ValueError:
            raise InvalidModuleInstanceNameError(module_instance_name)
        else:
            return self[module_name][replication_key]
