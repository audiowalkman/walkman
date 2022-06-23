from __future__ import annotations

import functools
import time
import typing

import pyo

import walkman

__all__ = (
    "PlayMixin",
    "JumpToMixin",
    "CloseMixin",
    "NamedMixin",
    "PyoObjectMixin",
    "DecibelMixin",
)


class PlayMixin(object):
    @property
    def is_playing(self) -> bool:
        try:
            return self._is_playing
        except AttributeError:
            return False

    def _play(self, duration: float = 0, delay: float = 0):
        ...

    def _stop(self, wait: float = 0):
        ...

    def play(self, duration: float = 0, delay: float = 0) -> PlayMixin:
        if not self.is_playing:
            self._play(duration=duration, delay=delay)
            self._is_playing = True
        return self

    def stop(self, wait: float = 0) -> PlayMixin:
        if self.is_playing:
            self._stop(wait=wait)
            self._is_playing = False
        return self


class JumpToMixin(object):
    def jump_to(self, time_in_seconds: float):
        ...


class TrackedPlayMixin(PlayMixin, JumpToMixin):
    @property
    def play_time(self) -> float:
        """Get time when 'play' method has been called"""
        return self._play_time

    @property
    def current_time(self) -> float:
        """Get current position of object"""
        return self._current_time

    def _jump_to(self, time_in_seconds: float):
        ...

    def _play(self, duration: float = 0, delay: float = 0):
        self._jump_to(self._current_time)
        self._play_time = time.time()

    def _stop(self, wait: float = 0):
        self._current_time = min(
            ((time.time() - self.play_time) + self.play_time, self.duration)
        )

    def jump_to(self, time_in_seconds: float):
        self._current_time = time_in_seconds
        self._jump_to(time_in_seconds)


class CloseMixin(object):
    def close(self) -> CloseMixin:
        return self


class NamedMixin(object):
    @classmethod
    def get_class_name(cls) -> str:
        # class name
        return walkman.utilities.camel_case_to_snake_case(cls.__name__)

    def get_instance_name(self) -> str:
        try:
            return self._instance_name
        except AttributeError:
            self._instance_name = f"{self.get_class_name()}-{id(self)}"
            return self.get_instance_name()

    def __str__(self) -> str:
        return f"{type(self).__name__}({self.get_instance_name()})"

    def __hash__(self) -> int:
        return hash(self.get_instance_name())


class PyoObjectMixin(object):
    @functools.cached_property
    def pyo_object(self) -> pyo.PyoObject:
        return pyo.Sig(0)

    @property
    def pyo_object_or_float(self) -> typing.Union[pyo.PyoObject, float]:
        return self.pyo_object


class DecibelMixin(object):
    @property
    def decibel(self) -> float:
        try:
            return self._decibel.getValue()
        except AttributeError:
            return -120

    @decibel.setter
    def decibel(self, value: float) -> float:
        try:
            self._decibel.setValue(value)
        except AttributeError:
            pass
