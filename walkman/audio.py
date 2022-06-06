from __future__ import annotations

import abc
import functools
import typing

import pyo

import walkman


class AudioObject(abc.ABC):
    @abc.abstractproperty
    def pyo_object(self) -> pyo.PyoObject:
        ...

    @classmethod
    def get_name(cls) -> str:
        return walkman.utilities.camel_case_to_snake_case(cls.__name__)

    def close(self):
        """Method is called when walkman is closed"""
        pass


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
        output_channel_mapping: walkman.ChannelMapping = walkman.ChannelMapping(
            {0: 0, 1: 1}
        ),
    ):
        self._is_playing = False
        self.server = pyo.Server(
            sr=sampling_rate,
            midi=midi,
            nchnls=output_channel_mapping.maxima_right_channel,
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
