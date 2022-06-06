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
    ):
        # If value is only a numerical value, we will only
        # pass it to 'pyo.Sig'
        self._sig = pyo.Sig(0)
        self._value = self._sig
        # Scale is used if a midi control input is used.
        # It get initialised with dummy values
        self._scale = pyo.Scale(self._sig)
        self._input_provider = input_provider

    @property
    def input_provider(self) -> walkman.InputProvider:
        return self._input_provider

    def initialise(
        self,
        value: float = 0,
        midi_control_index: typing.Optional[int] = None,
        midi_range: typing.Optional[typing.Tuple[float, float]] = None,
    ):
        value_control = None
        if midi_control_index is not None:
            try:
                value_control = self.input_provider.midi_input_list[midi_control_index]
            except IndexError:
                warnings.warn(
                    f"Found invalid midi_control_index = {midi_control_index}."
                    f" Only values from 0 to {len(self.input_provider.midi_input_list)}"
                    " are allowed. Ignored midi data.",
                    IllegalMidiControlIndexWarning,
                )
            if value_control and midi_range is not None:
                self._scale.setInput(value_control)
                self._scale.setInMin(value_control.minscale)
                self._scale.setInMax(value_control.maxscale)
                self._scale.setOutMin(midi_range[0])
                self._scale.setOutMax(midi_range[1])
                value_control = self._scale

        if value_control is None:
            self._sig.setValue(value)
            value_control = self._sig

        self._value = value_control

    @property
    def value(self) -> pyo.PyoObject:
        return self._value
