"""Define interface for modules"""

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


def override_default_kwargs(method_to_wrap: typing.Callable) -> typing.Callable:
    def wrapper(self, **kwargs):
        default_dict = copy.deepcopy(self.default_dict)
        default_dict.update(kwargs)
        return method_to_wrap(self, **default_dict)

    return wrapper


@dataclasses.dataclass
class Module(walkman.AudioObject):
    """Interface for an isolated audio process."""

    audio_host: walkman.AudioHost
    input_provider: walkman.InputProvider
    output_provider: walkman.OutputProvider
    auto_stop: bool = True
    fade_in_duration: float = 0.1
    fade_out_duration: float = 0.2
    default_dict: typing.Dict[str, typing.Any] = dataclasses.field(
        default_factory=lambda: {}
    )
    parameter_name_to_parameter_dict: typing.Dict[
        str, walkman.Parameter
    ] = dataclasses.field(default_factory=lambda: {})

    def __post_init__(self):
        self._is_playing = False
        self.fader = pyo.Fader(self.fade_in_duration, self.fade_out_duration)
        self.setup_pyo_object()
        self._pyo_object_with_fader = self._pyo_object * self.fader

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.get_name()})"

    @staticmethod
    def value_or_parameter_kwargs_to_parameter_kwargs(
        value_or_parameter_kwargs: typing.Union[dict, float]
    ) -> dict:
        if isinstance(value_or_parameter_kwargs, dict):
            parameter_kwargs = value_or_parameter_kwargs
        else:
            parameter_kwargs = {"value": value_or_parameter_kwargs}
        return parameter_kwargs

    @functools.cached_property
    def default_parameter_name_to_parameter_kwargs_dict(
        self,
    ) -> typing.Dict[str, typing.Dict[str, typing.Any]]:
        parameter_name_to_parameter_kwargs_dict = {}
        parameter_mapping_proxy = inspect.signature(self._initialise).parameters
        for parameter_name, inspect_parameter in parameter_mapping_proxy.items():
            if inspect_parameter.annotation == "walkman.Parameter":
                parameter_name_to_parameter_kwargs_dict.update(
                    {
                        parameter_name: self.value_or_parameter_kwargs_to_parameter_kwargs(
                            inspect_parameter.default
                        )
                    }
                )

        return parameter_name_to_parameter_kwargs_dict

    def _fetch_keyword_argument_dict(self, **kwargs) -> typing.Dict[str, typing.Any]:
        keyword_argument_dict = {}

        parameter_name_to_parameter_kwargs_dict = copy.deepcopy(
            self.default_parameter_name_to_parameter_kwargs_dict
        )

        for argument, value in kwargs.items():
            if argument in parameter_name_to_parameter_kwargs_dict:
                parameter_name_to_parameter_kwargs_dict[
                    argument
                ] = self.value_or_parameter_kwargs_to_parameter_kwargs(value)
            else:
                keyword_argument_dict.update({argument: value})

        for (
            parameter_name,
            parameter_kwargs,
        ) in parameter_name_to_parameter_kwargs_dict.items():
            try:
                parameter = self.parameter_name_to_parameter_dict[parameter_name]
            except KeyError:
                parameter = walkman.Parameter(self.input_provider)
                self.parameter_name_to_parameter_dict.update(
                    {parameter_name: parameter}
                )
            parameter.initialise(**parameter_kwargs)
            keyword_argument_dict.update({parameter_name: parameter})

        return keyword_argument_dict

    # ################## ABSTRACT PROPERTIES ################## #

    @abc.abstractproperty
    def _pyo_object(self) -> pyo.PyoObject:
        ...

    # ################## ABSTRACT METHODS ################## #

    @abc.abstractmethod
    def setup_pyo_object(self):
        ...

    @abc.abstractmethod
    def _initialise(self, **kwargs):  # type: ignore
        ...

    @abc.abstractmethod
    def _play(self, duration: float = 0, delay: float = 0):
        ...

    @abc.abstractmethod
    def _stop(self, wait: float = 0):
        ...

    # ################## PUBLIC PROPERTIES ################## #

    @property
    def pyo_object(self) -> pyo.PyoObject:
        return self._pyo_object_with_fader

    @property
    def duration(self) -> float:
        return 0

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    # ################## PUBLIC METHODS ################## #

    @override_default_kwargs
    def initialise(
        self,
        channel_mapping: typing.Optional[
            typing.Union[dict, walkman.ChannelMapping]
        ] = None,
        **kwargs,
    ):
        # Activate the channel mapping
        if channel_mapping is None:
            channel_mapping = walkman.ChannelMapping(
                {channel: channel for channel in range(len(self.pyo_object))}
            )
        else:
            channel_mapping = walkman.dict_or_channel_mapping_to_channel_mapping(
                channel_mapping
            )
        self.output_provider.activate_channel_mapping(self, channel_mapping)

        # Fetch parameters
        keyword_argument_dict = self._fetch_keyword_argument_dict(**kwargs)

        # Parse everything to actual initialise method
        self._initialise(**keyword_argument_dict)

    def play(self, duration: float = 0, delay: float = 0) -> Module:
        if not self.is_playing:
            self.fader.play(dur=duration, delay=delay)
            self._play(duration=duration, delay=delay)
            self._is_playing = True
        return self

    def stop(self, wait: float = 0) -> Module:
        if self.is_playing:
            self.fader.stop(wait)
            self._stop(wait + self.fade_out_duration)
            self._is_playing = False
        return self

    def close(self):
        self.stop()

    def jump_to(self, time_in_seconds: float):
        """To jump at certain points of the sound process.

        Can optionally be implemented.
        """

        pass


class ModuleWithDecibel(Module):
    def setup_pyo_object(self):
        # Default audio objects, used to control default parameter
        # 'decibel'
        self._amplitude = pyo.Sig(0)
        self._decibel_to_amplitude = pyo.DBToA(self._amplitude)
        self._decibel_signal_to = pyo.SigTo(self._decibel_to_amplitude, time=0.015)

    def _initialise(self, decibel: walkman.Parameter = -6, **kwargs):  # type: ignore
        self._amplitude.setValue(decibel.value)

    def _play(self, duration: float = 0, delay: float = 0):
        self._decibel_to_amplitude.play(delay=delay)
        self._decibel_signal_to.play(delay=delay)

    def _stop(self, wait: float = 0):
        self._decibel_to_amplitude.stop(wait=wait)
        self._decibel_signal_to.stop(wait=wait)


ModuleName = str


class ModuleDict(typing.Dict[ModuleName, typing.Tuple[Module, ...]]):
    @staticmethod
    def get_module_name_to_module_class_dict():
        namespace_package = __import__(walkman.constants.MODULE_PACKAGE_NAME)
        module_info_list = list(
            pkgutil.iter_modules(
                namespace_package.__path__, namespace_package.__name__ + "."
            )
        )
        module_name_to_module_class_dict = {}
        for module_info in module_info_list:
            module = importlib.import_module(module_info.name)
            for _, python_class in inspect.getmembers(module, inspect.isclass):
                if Module in inspect.getmro(python_class):
                    module_name_to_module_class_dict.update(
                        {python_class.get_name(): python_class}
                    )
        return module_name_to_module_class_dict

    @classmethod
    def from_audio_objects_and_module_configuration(
        cls,
        audio_host: walkman.AudioHost,
        input_provider: walkman.InputProvider,
        output_provider: walkman.OutputProvider,
        module_name_to_replication_configuration_dict: typing.Dict[
            str, typing.Dict[int, typing.Dict[str, typing.Any]]
        ],
    ) -> ModuleDict:
        module_name_to_module_class_dict = cls.get_module_name_to_module_class_dict()

        module_name_to_module_dict = {}
        for module_name, module_class in module_name_to_module_class_dict.items():
            try:
                replication_index_to_module_configuration_dict = (
                    module_name_to_replication_configuration_dict[module_name]
                )
            except KeyError:
                replication_index_to_module_configuration_dict = {0: {}}
            module_list = [
                None
                for _ in range(
                    max(replication_index_to_module_configuration_dict.keys()) + 1
                )
            ]
            for (
                replication_index,
                module_configuration,
            ) in replication_index_to_module_configuration_dict.items():
                module = module_class(
                    audio_host, input_provider, output_provider, **module_configuration
                )
                module_list[replication_index] = module
            module_tuple = tuple(
                module
                if module is not None
                else module_class(audio_host, input_provider, output_provider)
                for module in module_list
            )
            module_name_to_module_dict.update({module_name: module_tuple})
        return cls(module_name_to_module_dict)

    def close(self):
        for module in self.module_tuple:
            module.close()

    @functools.cached_property
    def module_tuple(self) -> typing.Tuple[walkman.Module, ...]:
        module_list = []
        for module_tuple in self.values():
            module_list.extend(module_tuple)
        return tuple(module_list)
