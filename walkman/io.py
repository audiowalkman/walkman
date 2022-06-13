"""This module handles input/output data of walkman."""

from __future__ import annotations
import dataclasses
import typing
import warnings

import pyo

import walkman


MidiControlNumber = int
MidiChannel = int
MidiControlList = typing.List[typing.Tuple[MidiControlNumber, MidiChannel]]
MidiInputList = typing.List[pyo.Midictl]

AudioInputList = typing.List[pyo.PyoObject]


@dataclasses.dataclass(frozen=True)
class InputProvider(object):
    """Collect all physical audio and control inputs"""

    audio_input_list: AudioInputList
    midi_input_list: MidiInputList

    @staticmethod
    def channel_mapping_to_audio_input_list(
        channel_mapping: walkman.ChannelMapping,
    ) -> AudioInputList:
        if not channel_mapping:
            return []

        physical_channel_index_to_input_dict = {}
        for physical_channel in channel_mapping.keys():
            pyo_input = pyo.Input(chnl=physical_channel)
            pyo_input.play()
            physical_channel_index_to_input_dict.update({physical_channel: pyo_input})

        denormal_noise = pyo.Noise(1e-24)
        denormal_noise.play()

        audio_input_list = [
            denormal_noise for _ in range(channel_mapping.maxima_left_channel)
        ]

        for physical_channel, audio_input_index_tuple in channel_mapping.items():
            pyo_input = physical_channel_index_to_input_dict[physical_channel]
            for audio_input_index in audio_input_index_tuple:
                audio_input_list[audio_input_index] += pyo_input

        return audio_input_list

    @staticmethod
    def midi_control_list_to_midi_input_list(
        midi_control_list: MidiControlList,
    ) -> MidiInputList:
        midi_input_list = []
        for midi_control_number, midi_channel in midi_control_list:
            midi_ctl = pyo.Midictl(midi_control_number, channel=midi_channel)
            midi_ctl.play()
            midi_input_list.append(midi_ctl)
        return midi_input_list

    @classmethod
    def from_data(
        cls,
        channel_mapping: typing.Union[
            dict, walkman.ChannelMapping
        ] = walkman.ChannelMapping({}),
        midi_control_list: MidiControlList = [],
    ) -> InputProvider:
        channel_mapping = walkman.dict_or_channel_mapping_to_channel_mapping(channel_mapping)
        audio_input_list = cls.channel_mapping_to_audio_input_list(channel_mapping)
        midi_input_list = cls.midi_control_list_to_midi_input_list(midi_control_list)
        return cls(audio_input_list=audio_input_list, midi_input_list=midi_input_list)


class IllegalChannelIndexWarning(Warning):
    """Call if user gave too high channel"""


MixerIndex = int
MixerInfo = typing.Tuple[MixerIndex, ...]
"""Each channel of an audio signal has a specific index in the mixer"""


class PyoObjectMixer(pyo.PyoObject):
    def __init__(self, base_objs: list):
        super().__init__()
        self._base_objs = base_objs


@dataclasses.dataclass
class OutputProvider(walkman.AudioObjectWithDecibel):
    """Collect all outputs from modules and send them to physical outputs"""

    channel_mapping: walkman.ChannelMapping = dataclasses.field(
        default_factory=lambda: walkman.ChannelMapping({0: 0, 1: 1})
    )
    output_mixer: pyo.Mixer = dataclasses.field(init=False)
    module_mixer: pyo.Mixer = dataclasses.field(init=False)
    module_channel_count: int = dataclasses.field(init=False)
    physical_output_channel_count: int = dataclasses.field(init=False)
    name_to_mixer_info: typing.Dict[str, MixerInfo] = dataclasses.field(
        default_factory=lambda: {}
    )

    def __post_init__(self):
        self.channel_mapping = walkman.dict_or_channel_mapping_to_channel_mapping(
            self.channel_mapping
        )
        self.module_channel_count = self.channel_mapping.maxima_left_channel
        self.physical_output_channel_count = self.channel_mapping.maxima_right_channel
        self.module_mixer = pyo.Mixer(outs=self.module_channel_count)

        self._decibel = pyo.SigTo(0)
        self._amplitude = pyo.DBToA(self._decibel)
        self.output_mixer = pyo.Mixer(
            outs=self.physical_output_channel_count, mul=self._amplitude
        )

        for (
            module_channel_index,
            physical_output_channel_index_tuple,
        ) in self.channel_mapping.items():
            pyo_object = PyoObjectMixer(self.module_mixer[module_channel_index])
            self.output_mixer.addInput(module_channel_index, pyo_object)
            for physical_output_channel_index in physical_output_channel_index_tuple:
                self.output_mixer.setAmp(
                    module_channel_index, physical_output_channel_index, 1
                )

        for channel_index, channel in enumerate(self.output_mixer):
            channel[0].out(chnl=channel_index)

    def _raise_illegal_audio_object_channel_warning(
        self,
        audio_object: walkman.AudioObject,
        channel_mapping: walkman.ChannelMapping,
        audio_object_channel_index: int,
    ):
        warnings.warn(
            "Found invalid audio_object_channel_index ="
            f" {audio_object_channel_index} in channel_mapping ="
            f" {channel_mapping} for audio object '{audio_object.name}'."
            f" Audio object only have {len(audio_object.pyo_object)}"
            " channels.",
            IllegalChannelIndexWarning,
        )

    @property
    def decibel(self) -> float:
        return self._decibel.getValue()

    @decibel.setter
    def decibel(self, value: float) -> float:
        self._decibel.setValue(value)

    def register_audio_object(
        self, simple_audio_object: walkman.SimpleAudioObject
    ) -> MixerInfo:
        mixer_info = []
        base_index = walkman.utilities.get_next_mixer_index(self.module_mixer)
        for audio_object_index in range(len(simple_audio_object.pyo_object)):
            pyo_channel = simple_audio_object.pyo_object[audio_object_index]
            mixer_index = base_index + audio_object_index
            self.module_mixer.addInput(mixer_index, pyo_channel)
            mixer_info.append(mixer_index)
        return tuple(mixer_info)

    def activate_channel_mapping(
        self,
        simple_audio_object: walkman.SimpleAudioObject,
        channel_mapping: walkman.ChannelMapping,
    ):
        name = simple_audio_object.name
        try:
            mixer_info = self.name_to_mixer_info[name]
        except KeyError:
            mixer_info = self.register_audio_object(simple_audio_object)
            self.name_to_mixer_info.update({name: mixer_info})

        for (
            audio_object_channel_index,
            output_channel_index_tuple,
        ) in channel_mapping.items():
            try:
                mixer_index = mixer_info[audio_object_channel_index]
            except IndexError:
                self._raise_illegal_audio_object_channel_warning(
                    simple_audio_object, channel_mapping, audio_object_channel_index
                )
            else:
                for module_output_channel_index in range(self.module_channel_count):
                    amplitude = int(
                        module_output_channel_index in output_channel_index_tuple
                    )
                    self.module_mixer.setAmp(
                        mixer_index, module_output_channel_index, amplitude
                    )
