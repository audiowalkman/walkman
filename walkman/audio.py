from __future__ import annotations

import abc
import functools
import uuid

import pyo

import walkman


class AudioObject(abc.ABC):
    @classmethod
    def get_name(cls) -> str:
        # class name
        return walkman.utilities.camel_case_to_snake_case(cls.__name__)

    @functools.cached_property
    def name(self) -> str:
        # unique instance name
        return f"{self.get_name()}-{uuid.uuid4()}"

    def close(self):
        """Method is called when walkman is closed"""
        pass


class SimpleAudioObject(AudioObject):
    @abc.abstractproperty
    def pyo_object(self) -> pyo.PyoObject:
        ...


class NestedAudioObject(AudioObject):
    @abc.abstractproperty
    def pyo_object_list(self) -> list[pyo.PyoObject]:
        ...


class AudioObjectWithDecibel(AudioObject):
    @abc.abstractproperty
    def decibel(self) -> float:
        ...

    @decibel.setter
    @abc.abstractproperty
    def decibel(self, decibel: float):
        ...


class AudioHost(object):
    """Wrapper for pyo.Server and pyo.Mixer.

    Simplifies server API and adds volumes controls.
    """

    def __init__(
        self,
        audio: str = "jack",
        midi: str = "jack",
        sampling_rate: int = 44100,
        buffer_size: int = 256,
        channel_count: int = 2,
    ):
        self._is_playing = False
        self.server = pyo.Server(
            sr=sampling_rate,
            midi=midi,
            nchnls=channel_count,
            buffersize=buffer_size,
            duplex=1,
            audio=audio,
            jackname=walkman.constants.NAME,
        ).boot()

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def start(self):
        self.server.start()
        self._is_playing = True

    def stop(self):
        self.server.stop()
        self._is_playing = False

    def close(self):
        self.stop()
        del self.server
