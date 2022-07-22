from __future__ import annotations

import functools
import typing
import warnings

import pyo

import walkman

from . import base

__all__ = (
    "ModuleWithUneffectivePlay",
    "ModuleWithUneffectiveStop",
    "Value",
    "Empty",
    "Parameter",
    "AudioInput",
    "MidiControlInput",
    "ModuleWithDecibel",
    "Sine",
    "Amplification",
    "Mixer",
    "Filter",
    "ConvolutionReverb",
    "WaveguideReverb",
    "ButterworthLowpassFilter",
    "ButterworthHighpassFilter",
    "Equalizer",
)


class ModuleWithUneffectiveStop(base.Module):
    def setup_pyo_object(self):
        super().setup_pyo_object()
        # XXX: Modules which inherit from 'ModuleWithUneffectiveStop' are expected
        #      to run when the software starts.
        self.initialise()
        self._play()

    def _stop_without_fader(self, wait: float = 0):
        ...

    def _stop(self, wait: float = 0):
        ...

    def stop(self, wait: float = 0) -> ModuleWithUneffectiveStop:
        return self


class ModuleWithUneffectivePlay(base.Module):
    def _play_without_fader(self, duration: float = 0, delay: float = 0):
        ...

    def _play(self, duration: float = 0, delay: float = 0):
        ...

    def play(self, duration: float = 0, delay: float = 0) -> ModuleWithUneffectivePlay:
        return self


class Value(ModuleWithUneffectivePlay, ModuleWithUneffectiveStop):
    def __init__(self, value: float = 0, **kwargs):
        self.value = value
        super().__init__(**kwargs)

    @property
    def pyo_object_or_float(self) -> float:
        return self.value


class Empty(base.Module):
    def _setup_pyo_object(self):
        self.signal = pyo.Sig(0)
        self.internal_pyo_object_list.append(self.signal)

    @property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.signal


class IllegalMidiControlIndexWarning(Warning):
    pass


DEFAULT_ENVELOPE_TYPE = "linear"


class UndefinedEnvelopeTypeWarning(Warning):
    def __init__(self, undefined_envelope_type: str):
        super().__init__(
            f"Found undefined envelope type '{undefined_envelope_type}'. "
            f"WALKMAN set envelope type to {DEFAULT_ENVELOPE_TYPE}."
        )


class Parameter(base.ModuleWithFader):
    ITEM_TO_VOICE_DICT = {
        "VALUE_VOICE": 0,
        "LINEAR_ENVELOPE_VOICE": 1,
        "EXPONENTIAL_ENVELOPE_VOICE": 2,
    }
    ENVELOPE_TYPE_TO_VOICE = {
        "linear": ITEM_TO_VOICE_DICT["LINEAR_ENVELOPE_VOICE"],
        "exponential": ITEM_TO_VOICE_DICT["EXPONENTIAL_ENVELOPE_VOICE"],
    }

    def __init__(
        self,
        fade_in_duration: float = 0.0001,
        fade_out_duration: float = 0.00001,
        **kwargs,
    ):
        super().__init__(
            fade_in_duration=fade_in_duration,
            fade_out_duration=fade_out_duration,
            **kwargs,
        )

    def _setup_pyo_object(
        self,
    ):
        super()._setup_pyo_object()

        # If value is only a numerical value, we will only
        # pass it to 'pyo.Sig'
        self.signal = pyo.Sig(0)
        # Scale is used if a midi control input is used.
        # It get initialised with dummy values
        self.linear_envelope = pyo.Linseg([(0, 0), (2, 0)])
        self.exponential_envelope = pyo.Expseg([(0, 0.1), (2, 0.1)])
        self.selector = pyo.Selector(
            [
                self.signal,
                self.linear_envelope,
                self.exponential_envelope,
            ]
        )
        self.portamento = pyo.Port(self.selector)

        self.ENVELOPE_TYPE_TO_ENVELOPE = {
            "linear": self.linear_envelope,
            "exponential": self.exponential_envelope,
        }

        self.internal_pyo_object_list.extend(
            [
                self.signal,
                self.linear_envelope,
                self.exponential_envelope,
                self.selector,
                self.portamento,
            ]
        )

        self.envelope_list = None
        self.envelope = None
        self.start_time: float = 0
        self.time: float = 0

    @property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.portamento

    @property
    def duration(self) -> float:
        return self.envelope_list[-1][0] if self.envelope_list else 0

    def _initialise(
        self,
        value: typing.Union[float, typing.List[typing.List[float]]] = 0,
        envelope_type: str = DEFAULT_ENVELOPE_TYPE,
        rise_time: float = 0.001,
        fall_time: float = 0.001,
        **kwargs,
    ):
        super()._initialise(**kwargs)
        self.portamento.setRiseTime(rise_time)
        self.portamento.setFallTime(fall_time)
        selector_voice = None
        envelope_list = None
        if isinstance(value, list):
            envelope_list = list(tuple(point) for point in value)
            try:
                envelope = self.ENVELOPE_TYPE_TO_ENVELOPE[envelope_type]
            except KeyError:
                envelope_type = DEFAULT_ENVELOPE_TYPE
                warnings.warn(envelope_type, UndefinedEnvelopeTypeWarning)
            finally:
                envelope = self.ENVELOPE_TYPE_TO_ENVELOPE[envelope_type]

            envelope.setList(envelope_list)
            selector_voice = self.ENVELOPE_TYPE_TO_VOICE[envelope_type]
            self.envelope = envelope

        else:
            self.signal.setValue(value)
            selector_voice = self.ITEM_TO_VOICE_DICT["VALUE_VOICE"]

        self.envelope_list = envelope_list
        self.selector.setVoice(selector_voice)
        self.time = 0


class ModuleWithDecibel(
    base.ModuleWithFader, decibel=base.AutoSetup(Value, module_kwargs={"value": 0})
):
    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        try:
            self.amplitude = pyo.DBToA(self.decibel.pyo_object_or_float)
        # If pyo_object_or_float returns a number this exception will be called
        except pyo.PyoArgumentTypeError:
            self.amplitude = walkman.utilities.decibel_to_amplitude_ratio(
                self.decibel.pyo_object_or_float
            )
            self.amplitude_signal_to = self.amplitude
        else:
            self.amplitude_signal_to = pyo.SigTo(self.amplitude, time=0.015)
            self.internal_pyo_object_list.extend(
                [self.amplitude, self.amplitude_signal_to]
            )


class AudioInput(ModuleWithDecibel):
    def __init__(self, input_channel_index: int = 0, **kwargs):
        super().__init__(**kwargs)
        self.input_channel_index = input_channel_index

    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        self.audio_input = pyo.Input(self.input_channel_index)
        self.denorm = pyo.Denorm(self.audio_input, mul=self.amplitude_signal_to)
        self.internal_pyo_object_list.extend([self.audio_input, self.denorm])

    @property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.denorm


class MidiControlInput(ModuleWithUneffectiveStop):
    def __init__(
        self,
        midi_control_number: int = 0,
        midi_channel: int = 0,
        initial_value: float = 0,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.initial_value = initial_value
        self.midi_control_number = midi_control_number
        self.midi_channel = midi_channel

    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        self.midi_input = pyo.Midictl(
            self.midi_control_number, channel=self.midi_channel, init=self.initial_value
        )
        self.internal_pyo_object_list.append(self.midi_input)

    def _initialise(self, minima: float = 0, maxima: float = 1, **kwargs):
        super()._initialise(**kwargs)
        self.midi_input.setMinScale(minima)
        self.midi_input.setMaxScale(maxima)

    @property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.midi_input


class Sine(
    ModuleWithDecibel,
    frequency=base.AutoSetup(Value, module_kwargs={"value": 1000}),
):
    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        self.sine = pyo.Sine(
            freq=self.frequency.pyo_object_or_float, mul=self.amplitude_signal_to
        )
        self.internal_pyo_object_list.append(self.sine)

    @property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.sine


class Amplification(
    ModuleWithDecibel,
    audio_input=base.Catch(walkman.constants.EMPTY_MODULE_INSTANCE_NAME),
):
    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        self.amplification = self.amplitude_signal_to * self.audio_input.pyo_object
        self.internal_pyo_object_list.append(self.amplification)

    @functools.cached_property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.amplification


class IllegalChannelIndexWarning(Warning):
    """Call if user gave too high channel"""


MixerIndex = int
MixerInfo = typing.Tuple[MixerIndex, ...]
"""Each channel of an audio signal has a specific index in the mixer"""

MixerAudioInputKeyPrefix = "audio_input_"
MixerAudioInputKeyPrefixCount = len(MixerAudioInputKeyPrefix)


class Mixer(
    ModuleWithDecibel,
    **{
        f"{MixerAudioInputKeyPrefix}{index}": base.Catch(
            walkman.constants.EMPTY_MODULE_INSTANCE_NAME, relevance=False
        )
        for index in range(100)
    },
):
    class PyoObjectMixer(pyo.PyoObject):
        def __init__(self, base_objs: list):
            super().__init__()
            self._base_objs = base_objs

    def __init__(
        self,
        channel_mapping: typing.Union[walkman.ChannelMapping, dict] = {0: 0, 1: 1},
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.channel_mapping = walkman.dict_or_channel_mapping_to_channel_mapping(
            channel_mapping
        )
        self.input_channel_count = self.channel_mapping.maxima_left_channel
        self.output_channel_count = self.channel_mapping.maxima_right_channel
        self.audio_input_key_to_mixer_info = {}

    def _setup_pyo_object(self):
        super()._setup_pyo_object()

        self.input_mixer = pyo.Mixer(outs=self.input_channel_count)
        self.output_mixer = pyo.Mixer(
            outs=self.output_channel_count, mul=self.amplitude_signal_to
        )

        for (
            input_channel_index,
            output_channel_index_tuple,
        ) in self.channel_mapping.items():
            local_pyo_object = self.PyoObjectMixer(
                self.input_mixer[input_channel_index]
            )
            self.output_mixer.addInput(input_channel_index, local_pyo_object)
            for output_channel_index in output_channel_index_tuple:
                self.output_mixer.setAmp(input_channel_index, output_channel_index, 1)

            self.internal_pyo_object_list.append(local_pyo_object)

        self.output_mixer_as_pyo_object = self.PyoObjectMixer(
            [channel[0] for channel in self.output_mixer]
        )

        self.internal_pyo_object_list.extend(
            [self.input_mixer, self.output_mixer, self.output_mixer_as_pyo_object]
        )

    @functools.cached_property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.output_mixer_as_pyo_object

    def _initialise(
        self, **audio_input_channel_mapping: typing.Dict[str, walkman.ChannelMapping]
    ):
        audio_input_key_to_channel_mapping_dict = {}
        for (
            audio_input_channel_mapping_key,
            channel_mapping,
        ) in audio_input_channel_mapping.items():
            audio_input_key, *_ = audio_input_channel_mapping_key.split(
                "_channel_mapping"
            )
            if audio_input_key in self.module_input_dict.keys():
                audio_input_key_to_channel_mapping_dict.update(
                    {audio_input_key: channel_mapping}
                )
            else:
                warnings.warn(
                    "Found invalid channel mapping "
                    f"argument '{audio_input_channel_mapping_key}'!"
                )

        for audio_input_key in self.module_input_dict.keys():
            if (
                audio_input_key[:MixerAudioInputKeyPrefixCount]
                == MixerAudioInputKeyPrefix
            ):
                module_instance = getattr(self, audio_input_key)
                if not isinstance(module_instance, Empty):
                    if audio_input_key not in audio_input_key_to_channel_mapping_dict:
                        channel_mapping = {}
                        for channel_index in range(len(module_instance.pyo_object)):
                            output_channel = channel_index % self.input_channel_count
                            channel_mapping.update({channel_index: output_channel})
                        audio_input_key_to_channel_mapping_dict.update(
                            {audio_input_key: channel_mapping}
                        )

        for (
            audio_input_key,
            channel_mapping,
        ) in audio_input_key_to_channel_mapping_dict.items():
            if isinstance(channel_mapping, (dict, walkman.ChannelMapping)):
                channel_mapping = walkman.dict_or_channel_mapping_to_channel_mapping(
                    channel_mapping
                )
                self.activate_channel_mapping(audio_input_key, channel_mapping)

    def _raise_illegal_audio_object_channel_warning(
        self,
        audio_input_key: str,
        channel_mapping: walkman.ChannelMapping,
        audio_object_channel_index: int,
    ):
        warnings.warn(
            "Found invalid audio_object_channel_index ="
            f" {audio_object_channel_index} in channel_mapping ="
            f" {channel_mapping} for audio input key '{audio_input_key}'.",
            IllegalChannelIndexWarning,
        )

    def register_audio_object(self, audio_input_key: str) -> typing.Optional[MixerInfo]:
        mixer_info_list = []
        base_index = walkman.utilities.get_next_mixer_index(self.input_mixer)
        try:
            pyo_object = getattr(self, audio_input_key).pyo_object
        except AttributeError:
            warnings.warn(
                f"No audio input with audio input key '{audio_input_key}' exists!"
                " WALKMAN ignored settings for invalid audio input key."
            )
            return None
        for audio_object_index in range(len(pyo_object)):
            pyo_channel = pyo_object[audio_object_index]
            mixer_index = base_index + audio_object_index
            self.input_mixer.addInput(mixer_index, pyo_channel)
            mixer_info_list.append(mixer_index)

        mixer_info = tuple(mixer_info_list)
        self.audio_input_key_to_mixer_info.update({audio_input_key: mixer_info})
        return mixer_info

    def activate_channel_mapping(
        self,
        audio_input_key: str,
        channel_mapping: walkman.ChannelMapping,
    ):
        try:
            mixer_info = self.audio_input_key_to_mixer_info[audio_input_key]
        except KeyError:
            mixer_info = self.register_audio_object(audio_input_key)
            if mixer_info is None:
                return

        for (
            audio_object_channel_index,
            output_channel_index_tuple,
        ) in channel_mapping.items():
            try:
                mixer_index = mixer_info[audio_object_channel_index]
            except IndexError:
                self._raise_illegal_audio_object_channel_warning(
                    audio_input_key, channel_mapping, audio_object_channel_index
                )
            else:
                for module_output_channel_index in range(self.input_channel_count):
                    amplitude = int(
                        module_output_channel_index in output_channel_index_tuple
                    )
                    self.input_mixer.setAmp(
                        mixer_index, module_output_channel_index, amplitude
                    )


class Filter(
    ModuleWithDecibel,
    frequency=base.AutoSetup(Value, module_kwargs={"value": 1000}),
    q=base.AutoSetup(Value, module_kwargs={"value": 5}),
    audio_input=base.Catch(walkman.constants.EMPTY_MODULE_INSTANCE_NAME),
):
    FILTER_TYPE_TO_INTERNAL_FILTER_TYPE = {
        "lowpass": 0,
        "highpass": 1,
        "bandpass": 2,
        "bandstop": 3,
        "allpass": 4,
    }

    def __init__(self, stages: int = 4, filter_type: str = "lowpass", **kwargs):
        super().__init__(**kwargs)
        self.stages = stages
        try:
            internal_filter_type = self.FILTER_TYPE_TO_INTERNAL_FILTER_TYPE[filter_type]
        except KeyError:
            default_filter_type = "lowpass"
            internal_filter_type = self.FILTER_TYPE_TO_INTERNAL_FILTER_TYPE[
                default_filter_type
            ]
            warnings.warn(
                f"Found undefined filter type '{filter_type}'."
                f"Filter type has been set to '{default_filter_type}'."
            )
        self.internal_filter_type = internal_filter_type

    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        self.audio_filter = pyo.Biquadx(
            self.audio_input.pyo_object,
            mul=self.amplitude_signal_to,
            freq=self.frequency.pyo_object_or_float,
            q=self.q.pyo_object_or_float,
            stages=self.stages,
            type=self.internal_filter_type,
        )
        self.internal_pyo_object_list.append(self.audio_filter)

    @functools.cached_property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.audio_filter


class ConvolutionReverb(
    ModuleWithDecibel,
    audio_input=base.Catch(walkman.constants.EMPTY_MODULE_INSTANCE_NAME),
    balance=base.AutoSetup(Value, module_kwargs={"value": 1}),
):
    def __init__(self, *, impulse_path: str, sample_size: int = 1024, **kwargs):
        super().__init__(**kwargs)
        self.impulse_path = impulse_path
        self.sample_size = sample_size

    def _setup_pyo_object(self):
        super()._setup_pyo_object()

        self.convolution_reverb = pyo.CvlVerb(
            self.audio_input.pyo_object,
            self.impulse_path,
            size=self.sample_size,
            mul=self.amplitude_signal_to,
            bal=self.balance.pyo_object_or_float,
        ).stop()

        self.internal_pyo_object_list.append(self.convolution_reverb)

    @functools.cached_property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.convolution_reverb


class WaveguideReverb(
    ModuleWithDecibel,
    audio_input=base.Catch(walkman.constants.EMPTY_MODULE_INSTANCE_NAME),
    balance=base.AutoSetup(Value, module_kwargs={"value": 1}),
    cutoff_frequency=base.AutoSetup(Value, module_kwargs={"value": 6000}),
    feedback=base.AutoSetup(Value, module_kwargs={"value": 0.6}),
):
    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        self.waveguide_reverb = pyo.WGVerb(
            self.audio_input.pyo_object,
            feedback=self.feedback.pyo_object_or_float,
            mul=self.amplitude_signal_to,
            bal=self.balance.pyo_object_or_float,
        ).stop()
        self.internal_pyo_object_list.append(self.waveguide_reverb)

    @functools.cached_property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.waveguide_reverb


class ButterworthLowpassFilter(
    ModuleWithDecibel,
    audio_input=base.Catch(walkman.constants.EMPTY_MODULE_INSTANCE_NAME),
    frequency=base.AutoSetup(Value, module_kwargs={"value": 1000}),
):
    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        self.lowpass_filter = pyo.ButLP(
            self.audio_input.pyo_object,
            mul=self.amplitude_signal_to,
            freq=self.frequency.pyo_object_or_float,
        ).stop()
        self.internal_pyo_object_list.append(self.lowpass_filter)

    @functools.cached_property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.lowpass_filter


class ButterworthHighpassFilter(
    ModuleWithDecibel,
    audio_input=base.Catch(walkman.constants.EMPTY_MODULE_INSTANCE_NAME),
    frequency=base.AutoSetup(Value, module_kwargs={"value": 1000}),
):
    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        self.highpass_filter = pyo.ButHP(
            self.audio_input.pyo_object,
            mul=self.amplitude_signal_to,
            freq=self.frequency.pyo_object_or_float,
        ).stop()
        self.internal_pyo_object_list.append(self.highpass_filter)

    @functools.cached_property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.highpass_filter


class Equalizer(
    ModuleWithDecibel,
    audio_input=base.Catch(walkman.constants.EMPTY_MODULE_INSTANCE_NAME),
    frequency=base.AutoSetup(Value, module_kwargs={"value": 500}),
    boost=base.AutoSetup(Value, module_kwargs={"value": -3}),
):
    FILTER_TYPE_TO_INTERNAL_FILTER_TYPE = {
        "peak": 0,
        "notch": 0,
        "lowshelf": 1,
        "highshelf": 2,
    }

    def __init__(self, filter_type: str = "peak", **kwargs):
        super().__init__(**kwargs)
        try:
            internal_filter_type = self.FILTER_TYPE_TO_INTERNAL_FILTER_TYPE[filter_type]
        except KeyError:
            default_filter_type = "peak"
            warnings.warn(
                f"Found undefined filter type '{filter_type}'."
                f"Filter type has been set to '{default_filter_type}'."
            )
            internal_filter_type = self.FILTER_TYPE_TO_INTERNAL_FILTER_TYPE[
                default_filter_type
            ]
        self.internal_filter_type = internal_filter_type

    def _setup_pyo_object(self):
        super()._setup_pyo_object()
        self.equalizer = pyo.EQ(
            self.audio_input.pyo_object,
            mul=self.amplitude_signal_to,
            freq=self.frequency.pyo_object_or_float,
            boost=self.boost.pyo_object_or_float,
            type=self.internal_filter_type,
        ).stop()
        self.internal_pyo_object_list.append(self.equalizer)

    def _initialise(self, q: float = 1, **kwargs):
        self.equalizer.setQ(q)
        super()._initialise(**kwargs)

    @functools.cached_property
    def _pyo_object(self) -> pyo.PyoObject:
        return self.equalizer
