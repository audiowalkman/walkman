from __future__ import annotations

import functools
import typing
import warnings

import pyo

import walkman

__all__ = (
    "PlayMixin",
    "JumpToMixin",
    "CloseMixin",
    "NamedMixin",
    "PyoObjectMixin",
    "PyoObjectMixinSwitch",
    "IllegalPyoObjectIndexWarning",
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
    """Mixin for objects which consist of one or more pyo objects."""

    @functools.cached_property
    def pyo_object(self) -> pyo.PyoObject:
        return pyo.Sig(0)

    @property
    def pyo_object_or_float(self) -> pyo.PyoObject | float:
        return self.pyo_object

    @functools.cached_property
    def pyo_object_tuple(self) -> tuple[pyo.PyoObject, ...]:
        return (self.pyo_object,)

    @functools.cached_property
    def pyo_object_count(self) -> int:
        return len(self.pyo_object_tuple)


class PyoObjectMixinSwitch(object):
    """Wrap PyoObjectMixin instance to select default pyo object.

    Because instances of PyoObjectMixin can have multiple pyo objects,
    but still the convenient 'pyo_object' property, we need to find a cheap
    way to set the default 'pyo_object'. This object wraps any PyoObjectMixin.
    It's still mostly the same as if you would directly use the original object,
    apart from the the additional 'pyo_object_index' attribute and 'switch' method
    and that the 'pyo_object' property is overriden by

        ORGINAL_OBJECT.pyo_object_tuple[WRAPPER.pyo_object_index]
    """

    def __init__(self, pyo_object_mixin: PyoObjectMixin):
        self._pyo_object_mixin = pyo_object_mixin

    def __getattribute__(self, attr: str) -> typing.Any:
        if attr in _PYO_OBJECT_SWITCH_ACCESS_TUPLE:
            return super().__getattribute__(attr)
        if attr == "pyo_object":
            # We can't figure out whether a 'pyo_object_index' is too
            # when initially setting the attribute, because the pyo object
            # isn't set up yet (and we have to wait until the whole input chain
            # is clear inside ModuleContainer initialization routine). So we
            # can only catch the problem here, but we auto set it to an ok
            # value, so that walkman doesn't break.
            try:
                return self._pyo_object_mixin.pyo_object_tuple[self.pyo_object_index]
            except IndexError:
                warnings.warn(IllegalPyoObjectIndexWarning(self))
                self.pyo_object_index = 0
                return self.pyo_object
        return getattr(self._pyo_object_mixin, attr)

    def __setattr__(self, attr: str, value: typing.Any):
        if attr in _PYO_OBJECT_SWITCH_ACCESS_TUPLE:
            return super().__setattr__(attr, value)
        return setattr(self._pyo_object_mixin, attr, value)

    def __str__(self) -> str:
        return f"W({str(self._pyo_object_mixin)}, i={self.pyo_object_index})"

    def __repr__(self) -> str:
        return f"W({repr(self._pyo_object_mixin)}, i={self.pyo_object_index})"

    @property
    def pyo_object_index(self) -> int:
        try:
            return self._pyo_object_index
        except AttributeError:  # Fallback if initial setting fails.
            return 0

    @pyo_object_index.setter
    def pyo_object_index(self, pyo_object_index: int):
        self._pyo_object_index = pyo_object_index

    @property
    def base(self) -> PyoObjectMixin:
        return self._pyo_object_mixin

    def switch(self, pyo_object_index: int) -> PyoObjectMixinSwitch:
        # Shallow copy is sufficient, because we don't want to copy
        # the underlying '_pyo_object_mixin', we only want to switch
        # the default 'pyo_object'.
        s = type(self)(self._pyo_object_mixin)
        s.pyo_object_index = pyo_object_index
        return s


class IllegalPyoObjectIndexWarning(Warning):
    def __init__(self, pyo_object_mixin_switch: PyoObjectMixinSwitch):
        super().__init__(
            f"Problem with module '{pyo_object_mixin_switch}': Can't get pyo_object with pyo_object_index "
            f"'{pyo_object_mixin_switch.pyo_object_index}', because"
            f" object '{pyo_object_mixin_switch._pyo_object_mixin}' only has "
            f"'{pyo_object_mixin_switch.pyo_object_count}' pyo objects. "
            "'pyo_object_index' has been autoset to 0."
        )


_PYO_OBJECT_SWITCH_ACCESS_TUPLE = (
    "pyo_object_index",
    "_pyo_object_index",
    "_pyo_object_mixin",
    "switch",
    "base",
)


class DecibelMixin(object):
    @property
    def decibel(self) -> float:
        try:
            return self._decibel.getValue()
        except AttributeError:
            return -120

    @decibel.setter
    def decibel(self, value: float):
        try:
            self._decibel.setValue(value)
        except AttributeError:
            pass
