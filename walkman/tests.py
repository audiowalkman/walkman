import dataclasses
import functools
import itertools
import typing
import uuid

import pyo

import walkman


@dataclasses.dataclass
class AudioTest(walkman.NestedAudioObject):
    output_channel_mapping: walkman.ChannelMapping
    internal_pyo_object_list: typing.List[pyo.PyoObject] = dataclasses.field(
        default_factory=lambda: []
    )

    @functools.cached_property
    def name(self) -> str:
        return str(uuid.uuid4())

    def get_name(self):
        return self.name

    def close(self):
        # Remove any test traces
        for internal_pyo_object in self.internal_pyo_object_list:
            internal_pyo_object.stop()
            del internal_pyo_object


@dataclasses.dataclass
class AudioRotationTest(AudioTest):
    inner_channel_index: int = 0
    play_duration: float = 1

    def __post_init__(self):
        self.inner_channel_tuple = tuple(sorted(self.output_channel_mapping.keys()))
        self._channel_index_cycle = itertools.cycle(
            range(len(self.inner_channel_tuple))
        )
        self._decibel = -120
        self.decibel_signal = pyo.SigTo(self._decibel)
        self.decibel_to_amplitude = pyo.DBToA(self.decibel_signal)
        self.fader = pyo.Fader()
        self.noise = pyo.Noise(mul=self.fader * self.decibel_to_amplitude)
        self.mixer = self.output_channel_mapping.to_mixer()
        self.mixer.addInput(0, self.noise)
        self.pattern = pyo.Pattern(self._increment, self.play_duration + 0.075)
        self.pattern.stop()
        self.internal_pyo_object_list.extend(
            [
                self.pattern,
                self.mixer,
                self.noise,
                self.fader,
                self.decibel_signal,
                self.decibel_to_amplitude,
            ]
        )
        for output_index, channel in enumerate(self.mixer):
            channel[0].out(output_index)

    def _increment(self):
        self.inner_channel_index = next(self._channel_index_cycle)
        walkman.constants.LOGGER.info(
            f"{type(self).__name__}: Test channel {self.channel_index}."
        )
        output_channel_tuple = self.output_channel_tuple
        for output_channel_index in range(
            self.output_channel_mapping.maxima_right_channel
        ):
            amplitude = output_channel_index in output_channel_tuple
            self.mixer.setAmp(0, output_channel_index, amplitude)
        self.fader.play(dur=self.play_duration)

    @property
    def decibel(self) -> float:
        return self._decibel

    @decibel.setter
    def decibel(self, decibel: float):
        self.decibel_signal.setValue(decibel)

    @property
    def channel_index(self) -> int:
        return self.inner_channel_tuple[self.inner_channel_index]

    @property
    def output_channel_tuple(self) -> typing.Tuple[int]:
        return self.output_channel_mapping[self.channel_index]

    @property
    def pyo_object_list(self) -> typing.List[pyo.PyoObject]:
        return self.internal_pyo_object_list

    def play(self):
        self.pattern.play()
        self.noise.play()

    def stop(self):
        self.pattern.stop()
        self.noise.stop()
