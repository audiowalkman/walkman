import typing
import warnings

import pyo

import walkman


class IllegalMidiControlIndexWarning(Warning):
    pass


class Parameter(object):
    def __init__(
        self,
        input_provider: walkman.InputProvider,
        value: float = 0,
        midi_control_index: typing.Optional[int] = None,
        midi_range: typing.Optional[typing.Tuple[float, float]] = None,
    ):
        value_control = None
        if midi_control_index is not None:
            try:
                value_control = input_provider.midi_input_list[midi_control_index]
            except IndexError:
                warnings.warn(
                    f"Found invalid midi_control_index = {midi_control_index}."
                    f" Only values from 0 to {len(input_provider.midi_input_list)}"
                    " are allowed. Ignored midi data.",
                    IllegalMidiControlIndexWarning,
                )
            if value_control and midi_range is not None:
                scale = pyo.Scale(
                    value_control,
                    value_control.minscale,
                    value_control.maxscale,
                    *midi_range,
                )
                value_control = scale

        if value_control is None:
            value_control = pyo.Sig(value)

        self._value = value_control

    @property
    def value(self) -> pyo.PyoObject:
        return self._value
