from __future__ import annotations

import time
import typing
import warnings

import pyo

import walkman


class IllegalMidiControlIndexWarning(Warning):
    pass


DEFAULT_ENVELOPE_TYPE = "linear"


class UndefinedEnvelopeTypeWarning(Warning):
    def __init__(self, undefined_envelope_type: str):
        super().__init__(
            f"Found undefined envelope type '{undefined_envelope_type}'. "
            f"WALKMAN set envelope type to {DEFAULT_ENVELOPE_TYPE}."
        )


class Parameter(object):
    # Constants
    # 0 is value, 1 is scale object,
    # 2 is linear envelope, 3 is exponential envelope,
    # everything above are midi control inputs.
    ITEM_TO_VOICE_DICT = {
        "VALUE_VOICE": 0,
        "SCALE_VOICE": 1,
        "LINEAR_ENVELOPE_VOICE": 2,
        "EXPONENTIAL_ENVELOPE_VOICE": 3,
    }
    ITEM_COUNT = len(ITEM_TO_VOICE_DICT)

    ENVELOPE_TYPE_TO_VOICE = {
        "linear": ITEM_TO_VOICE_DICT["LINEAR_ENVELOPE_VOICE"],
        "exponential": ITEM_TO_VOICE_DICT["EXPONENTIAL_ENVELOPE_VOICE"],
    }

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
        self._linear_envelope = pyo.Linseg([(0, 0), (2, 0)])
        self._exponential_envelope = pyo.Expseg([(0, 0.1), (2, 0.1)])
        self._value = pyo.Selector(
            [self._sig, self._scale, self._linear_envelope, self._exponential_envelope]
            + self.input_provider.midi_input_list
        )

        self.ENVELOPE_TYPE_TO_ENVELOPE = {
            "linear": self._linear_envelope,
            "exponential": self._exponential_envelope,
        }

        self._envelope_list = None
        self._envelope = None
        self._start_time: float = 0
        self._time: float = 0

    @property
    def input_provider(self) -> walkman.InputProvider:
        return self._input_provider

    @property
    def value(self) -> pyo.PyoObject:
        return self._value

    @property
    def duration(self) -> float:
        return self._envelope_list[-1][0] if self._envelope_list else 0

    def initialise(
        self,
        value: typing.Union[float, typing.List[typing.List[float]]] = 0,
        midi_control_index: typing.Optional[int] = None,
        midi_range: typing.Optional[typing.Tuple[float, float]] = None,
        envelope_type: str = DEFAULT_ENVELOPE_TYPE,
    ):
        selector_voice = None
        envelope_list = None
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
                selector_voice = self.ITEM_COUNT + midi_control_index

            if selector_voice and midi_range is not None:
                self._scale.setInput(value_control)
                self._scale.setInMin(value_control.minscale)
                self._scale.setInMax(value_control.maxscale)
                self._scale.setOutMin(midi_range[0])
                self._scale.setOutMax(midi_range[1])
                selector_voice = self.ITEM_TO_VOICE_DICT["SCALE_VOICE"]

        if selector_voice is None:
            if isinstance(value, list):
                value = list(tuple(point) for point in value)
                try:
                    envelope = self.ENVELOPE_TYPE_TO_ENVELOPE[envelope_type]
                except KeyError:
                    envelope_type = DEFAULT_ENVELOPE_TYPE
                    warnings.warn(envelope_type, UndefinedEnvelopeTypeWarning)
                finally:
                    envelope = self.ENVELOPE_TYPE_TO_ENVELOPE[envelope_type]

                envelope.setList(value)
                selector_voice = self.ENVELOPE_TYPE_TO_VOICE[envelope_type]
                envelope_list = value
                self._envelope = envelope

            else:
                self._sig.setValue(value)
                value_control = self._sig
                selector_voice = self.ITEM_TO_VOICE_DICT["VALUE_VOICE"]

        self._envelope_list = envelope_list
        self._value.setVoice(selector_voice)
        self._time = 0

    # TODO(Ensure parameter starts at correct time when stopping in between)
    def play(self, duration: float = 0, delay: float = 0) -> Parameter:
        self._start_time = time.time()
        if self._envelope:
            self._envelope.play(duration, delay)
        return self

    def stop(self, wait: float = 0) -> Parameter:
        self._time = time.time() - self._start_time
        if self._envelope:
            self._envelope.stop(wait)
        return self
