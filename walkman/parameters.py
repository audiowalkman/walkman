import typing
import warnings

import pyo

import walkman


class IllegalMidiControlIndexWarning(Warning):
    pass


class Parameter(object):
    # Constants
    # 0 is value, 1 is scale object,
    # everything above are midi control inputs.
    VALUE_VOICE: int = 0
    SCALE_VOICE: int = 1

    def __init__(
        self,
        input_provider: walkman.InputProvider,
    ):
        # If value is only a numerical value, we will only
        # pass it to 'pyo.Sig'
        self._sig = pyo.Sig(0)
        # Scale is used if a midi control input is used.
        # It get initialised with dummy values
        self._scale = pyo.Scale(self._sig)
        self._input_provider = input_provider
        self._value = pyo.Selector(
            [self._sig, self._scale] + self.input_provider.midi_input_list
        )

    @property
    def input_provider(self) -> walkman.InputProvider:
        return self._input_provider

    def initialise(
        self,
        value: float = 0,
        midi_control_index: typing.Optional[int] = None,
        midi_range: typing.Optional[typing.Tuple[float, float]] = None,
    ):
        selector_voice = None
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
            else:
                selector_voice = 2 + midi_control_index

            if selector_voice and midi_range is not None:
                self._scale.setInput(value_control)
                self._scale.setInMin(value_control.minscale)
                self._scale.setInMax(value_control.maxscale)
                self._scale.setOutMin(midi_range[0])
                self._scale.setOutMax(midi_range[1])
                selector_voice = self.SCALE_VOICE

        if selector_voice is None:
            self._sig.setValue(value)
            value_control = self._sig
            selector_voice = self.VALUE_VOICE

        self._value.setVoice(selector_voice)

    @property
    def value(self) -> pyo.PyoObject:
        return self._value
