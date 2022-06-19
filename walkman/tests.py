import dataclasses
import functools
import itertools
import typing
import uuid

import pyo

import walkman


@dataclasses.dataclass
class AudioTest(object):
    channel_count: int
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
    play_duration: float = 1

    def __post_init__(self):
        self._channel_index_cycle = itertools.cycle(range(self.channel_count))
        self._decibel = -120
        self.decibel_signal = pyo.SigTo(self._decibel)
        self.decibel_to_amplitude = pyo.DBToA(self.decibel_signal)
        self.fader = pyo.Fader()
        self.noise = pyo.Noise(mul=self.fader * self.decibel_to_amplitude)
        self.mixer = pyo.Mixer(outs=self.channel_count)
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
        channel_index = next(self._channel_index_cycle)
        walkman.constants.LOGGER.info(
            f"{type(self).__name__}: Test channel {channel_index}."
        )
        for output_channel_index in range(self.channel_count):
            amplitude = output_channel_index == channel_index
            self.mixer.setAmp(0, output_channel_index, amplitude)
        self.fader.play(dur=self.play_duration)

    @property
    def decibel(self) -> float:
        return self._decibel

    @decibel.setter
    def decibel(self, decibel: float):
        self.decibel_signal.setValue(decibel)

    @property
    def pyo_object_list(self) -> typing.List[pyo.PyoObject]:
        return self.internal_pyo_object_list

    def play(self):
        self.pattern.play()
        self.noise.play()

    def stop(self):
        self.pattern.stop()
        self.noise.stop()
