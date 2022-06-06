"""Define interface for modules"""

from __future__ import annotations

import abc
import dataclasses
import importlib
import inspect
import pkgutil
import typing

import pyo

import walkman


@dataclasses.dataclass
class Module(walkman.AudioObject):
    """Interface for an isolated audio process."""

    audio_host: walkman.AudioHost
    input_provider: walkman.InputProvider
    output_provider: walkman.OutputProvider
    auto_stop: bool = True
    fade_in_duration: float = 0.001
    fade_out_duration: float = 0.01
    default_dict: typing.Dict[str, typing.Any] = dataclasses.field(
        default_factory=lambda: {}
    )

    def __post_init__(self):
        self._is_playing = False
        self.fader = pyo.Fader(self.fade_in_duration, self.fade_out_duration)
        self.setup_pyo_object()
        self._pyo_object_with_fader = self._pyo_object * self.fader

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.get_name()})"

    def _fetch_keyword_argument_dict(self, **kwargs) -> typing.Dict[str, typing.Any]:
        def value_or_parameter_kwargs_to_parameter_kwargs(
            value_or_parameter_kwargs: typing.Union[dict, float]
        ) -> dict:
            if isinstance(value_or_parameter_kwargs, dict):
                parameter_kwargs = value_or_parameter_kwargs
            else:
                parameter_kwargs = {"value": value_or_parameter_kwargs}
            return parameter_kwargs

        parameter_name_to_parameter_kwargs_dict = {}
        parameter_mapping_proxy = inspect.signature(self._initalise).parameters
        for parameter_name, inspect_parameter in parameter_mapping_proxy.items():
            if inspect_parameter.annotation == "walkman.Parameter":
                parameter_name_to_parameter_kwargs_dict.update(
                    {
                        parameter_name: value_or_parameter_kwargs_to_parameter_kwargs(
                            inspect_parameter.default
                        )
                    }
                )

        keyword_argument_dict = {}
        keyword_argument_dict.update(self.default_dict)

        for argument, value in kwargs.items():
            if argument in parameter_name_to_parameter_kwargs_dict:
                parameter_name_to_parameter_kwargs_dict[
                    argument
                ] = value_or_parameter_kwargs_to_parameter_kwargs(value)
            else:
                keyword_argument_dict.update({argument: value})

        for (
            parameter_name,
            parameter_kwargs,
        ) in parameter_name_to_parameter_kwargs_dict.items():
            parameter = walkman.Parameter(self.input_provider, **parameter_kwargs)
            # parameter = parameter_kwargs['value']
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
    def _initalise(self, decibel: walkman.Parameter = -6, **kwargs):  # type: ignore
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
        self._initalise(**keyword_argument_dict)

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


ModuleName = str


class ModuleDict(typing.Dict[ModuleName, Module]):
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
        module_name_to_module_configuration_dict: typing.Dict[
            str, typing.Dict[str, typing.Any]
        ],
    ) -> ModuleDict:
        module_name_to_module_class_dict = cls.get_module_name_to_module_class_dict()

        module_name_to_module_dict = {}
        for module_name, module_class in module_name_to_module_class_dict.items():
            try:
                module_configuration = module_name_to_module_configuration_dict[
                    module_name
                ]
            except KeyError:
                module_configuration = {}
            module = module_class(
                audio_host, input_provider, output_provider, **module_configuration
            )
            module_name_to_module_dict.update({module_name: module})
        return cls(module_name_to_module_dict)

    def close(self):
        for module in self.values():
            module.close()
