from __future__ import annotations
from walkman.utilities import decibel_to_amplitude_ratio

import pyo

import walkman

__all__ = ("AudioHost",)


class AudioHost(walkman.PlayMixin, walkman.CloseMixin, walkman.DecibelMixin):
    """Wrapper for pyo.Server.

    Simplifies server API.
    """

    def __init__(
        self,
        audio: str = "jack",
        midi: str = "jack",
        sampling_rate: int = 44100,
        buffer_size: int = 1024,
        channel_count: int = 2,
        **kwargs,
    ):
        self.channel_count = channel_count
        self.server = pyo.Server(
            sr=sampling_rate,
            midi=midi,
            nchnls=channel_count,
            buffersize=buffer_size,
            duplex=1,
            audio=audio,
            jackname=f"{walkman.constants.NAME}_{channel_count}",
            **kwargs,
        ).boot()
        self.decibel = -12

    def _play(self, **_):
        self.server.start()

    def _stop(self, wait: float = 0):
        self.server.stop()

    def close(self):
        self.stop()
        del self.server

    @property
    def decibel(self) -> float:
        return self._decibel

    @decibel.setter
    def decibel(self, decibel: float):
        self._decibel = decibel
        self.server.setAmp(float(1 * (10 ** (decibel / 20))))
