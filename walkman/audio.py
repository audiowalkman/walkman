"""Handle audio playback for walkman"""

from __future__ import annotations
import abc
import functools
import time
import tempfile
import typing
import warnings

import numpy as np
import pyo
import soundfile

import walkman

FrameCount = int
DurationInSeconds = float
SamplingRate = int
ChannelCount = int
FileFormat = str
SampleType = str


class ChannelMapping(typing.Dict[int, typing.Tuple[int, ...]]):
    """Map sound file channel to physical outputs"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hack to ensure key/values are integer
        key_to_remove_list = []
        update_dict = {}
        for key, value in self.items():
            if not isinstance(key, int):
                key_to_remove_list.append(key)
            if isinstance(value, (str, int)):
                output_channel_list = [value]
            else:
                output_channel_list = value
            output_channel_tuple = tuple(
                int(output_channel) for output_channel in output_channel_list
            )
            update_dict[int(key)] = output_channel_tuple
        self.update(update_dict)
        for key in key_to_remove_list:
            del self[key]

    @property
    def output_channel_tuple_tuple(self) -> typing.Tuple[typing.Tuple[int, ...], ...]:
        return tuple(self.values())

    @property
    def output_channel_set(self) -> typing.Set[int, ...]:
        output_channel_set = set([])
        for output_channel_tuple in self.output_channel_tuple_tuple:
            for output_channel in output_channel_tuple:
                output_channel_set.add(output_channel)
        return output_channel_set

    @property
    def maxima_output_channel(self) -> int:
        return max(self.output_channel_set) + 1

    def to_mixer(self) -> pyo.Mixer:
        return pyo.Mixer(outs=self.maxima_output_channel)


class NotEnoughChannelWarning(Warning):
    """Hint if user given soundfiles don't have enough channels"""


class SoundFile(object):
    """Initialize a sound file"""

    def __init__(
        self,
        name: str,
        path: str,
        loop: bool = False,
        decibel: float = 0,
        # In case SoundFile is available as a temporary file (because
        # channels have been added) we have to pass the
        # temporary_file to the object in order to avoid that
        # the garbage collector closes the file.
        temporary_file: typing.Optional[tempfile.NamedTemporaryFile] = None,
    ):
        self.name = name
        self.path = str(path)
        self.loop = loop
        self.temporary_file = temporary_file
        self._decibel = decibel

    @staticmethod
    def decibel_to_amplitude_ratio(
        decibel: float, reference_amplitude: float = 1
    ) -> float:
        """Convert decibel to amplitude ratio.

        :param decibel: The decibel number that shall be converted.
        :param reference_amplitude: The amplitude for decibel == 0.

        """
        return float(reference_amplitude * (10 ** (decibel / 20)))

    def close(self):
        if self.temporary_file is not None:
            self.temporary_file.close()

    @functools.cached_property
    def information_tuple(
        self,
    ) -> typing.Tuple[
        FrameCount,
        DurationInSeconds,
        SamplingRate,
        ChannelCount,
        FileFormat,
        SampleType,
    ]:
        return pyo.sndinfo(self.path)

    @functools.cached_property
    def frame_count(self) -> FrameCount:
        return self.information_tuple[0]

    @functools.cached_property
    def duration_in_seconds(self) -> DurationInSeconds:
        return self.information_tuple[1]

    @functools.cached_property
    def sampling_rate(self) -> SamplingRate:
        return self.information_tuple[2]

    @functools.cached_property
    def channel_count(self) -> ChannelCount:
        return self.information_tuple[3]

    @functools.cached_property
    def file_format(self) -> FileFormat:
        return self.information_tuple[4]

    @functools.cached_property
    def sample_type(self) -> SampleType:
        return self.information_tuple[5]

    @property
    def amplitude(self) -> float:
        return SoundFile.decibel_to_amplitude_ratio(self.decibel)

    @property
    def decibel(self) -> float:
        return self._decibel

    def _expand_sound_file(self, path: str, channel_to_add_count: int):
        original_sound_file, sampling_rate = soundfile.read(self.path)
        if original_sound_file.ndim == 1:
            new_sound_file = original_sound_file[..., np.newaxis]
        else:
            new_sound_file = original_sound_file

        zero_array = np.zeros([len(original_sound_file)])
        zero_array = zero_array[..., np.newaxis]

        new_sound_file = np.hstack(
            [new_sound_file] + ([zero_array] * channel_to_add_count)
        )
        soundfile.write(path, new_sound_file, sampling_rate, format="wav")

    def expand_to(self, channel_count: int) -> SoundFile:
        difference = channel_count - self.channel_count
        if difference > 0:
            warnings.warn(
                f"SoundFile '{self.name}' misses {difference} channels. "
                f"{walkman.constants.NAME} automatically added {difference}"
                " silent channels.",
                NotEnoughChannelWarning,
            )
            temporary_file = tempfile.NamedTemporaryFile()
            new_path = temporary_file.name
            self._expand_sound_file(new_path, difference)
            expanded_sound_file = type(self)(
                name=self.name,
                path=new_path,
                loop=self.loop,
                temporary_file=temporary_file,
                decibel=self.decibel,
            )
            return expanded_sound_file
        elif difference < 0:
            raise ValueError(
                "Can't expand SoundFile with "
                f"channel_count = {self.channel_count}"
                f"to only {channel_count} channels!"
            )
        else:
            return self


class SoundFilePlayer(abc.ABC):
    def __init__(self, sound_file: typing.Optional[SoundFile], loop: bool = False):
        self.sound_file = sound_file
        self.loop = loop

    @abc.abstractproperty
    def pyo_object(self) -> pyo.PyoObject:
        ...

    @abc.abstractproperty
    def is_playing(self) -> bool:
        ...

    @abc.abstractmethod
    def play(self, duration: float = 0, delay: float = 0):
        ...

    @abc.abstractmethod
    def stop(self):
        ...

    @abc.abstractmethod
    def jump_to(self, time_in_seconds: float):
        ...


def reset_sound_file_attribute(method_to_wrap: typing.Callable) -> typing.Callable:
    def wrapper(self, *args, **kwargs):
        if is_playing := self.is_playing:
            self.stop()
        return_value = method_to_wrap(self, *args, **kwargs)
        if is_playing:
            self.play(delay=self.delay)
        return return_value

    return wrapper


class SoundFilePlayerDisk(SoundFilePlayer):
    """Play sound file from disk.

    Can be expensive for CPU, but saves RAM.
    """

    delay = 0.35

    def __init__(self, *args, **kwargs):
        self._is_playing = False
        self.sig_to = pyo.SigTo(value=0, time=self.delay)
        super().__init__(*args, **kwargs)

    @property
    def amplitude(self) -> float:
        return self.sig_to.value

    @amplitude.setter
    def amplitude(self, value: float):
        self.sig_to.value = value

    @property
    def amplitude_factor(self) -> float:
        try:
            sound_file_player = self._sound_file_player
        except AttributeError:
            return 0
        else:
            return sound_file_player.mul

    @amplitude_factor.setter
    def amplitude_factor(self, amplitude_factor: float):
        try:
            sound_file_player = self._sound_file_player
        except AttributeError:
            pass
        else:
            sound_file_player.mul = amplitude_factor

    @property
    def is_playing(self) -> bool:
        is_playing = self._is_playing
        try:
            sound_file_player = self._sound_file_player
        except AttributeError:
            pass
        else:
            if is_playing and not sound_file_player.isPlaying():
                self._is_playing = is_playing = False
        return is_playing

    @property
    def pyo_object(self) -> pyo.PyoObject:
        try:
            pyo_object = self._pyo_object
        except AttributeError:
            try:
                sound_file_player = self._sound_file_player
            except AttributeError:
                return
            else:
                self._pyo_object = pyo_object = sound_file_player * self.sig_to
        return pyo_object

    @property
    def sound_file(self) -> SoundFile:
        return self._sound_file

    @sound_file.setter
    @reset_sound_file_attribute
    def sound_file(self, sound_file: SoundFile):
        try:
            sound_file_player = self._sound_file_player
        except AttributeError:
            self._sound_file_player = pyo.SfPlayer(sound_file.path).stop()
        else:
            sound_file_player.setPath(sound_file.path)
        finally:
            self.loop = sound_file.loop
            self.amplitude = sound_file.amplitude
        self._sound_file = sound_file

    @property
    def loop(self) -> bool:
        return self._loop

    @loop.setter
    @reset_sound_file_attribute
    def loop(self, loop: bool):
        self._loop = loop
        try:
            sound_file_player = self._sound_file_player
        # In first init block sound_file_to_play won't
        # be added yet.
        except AttributeError:
            pass
        else:
            sound_file_player.setLoop(loop)

    def play(self, duration: float = 0, delay: float = 0):
        self._is_playing = True
        self._sound_file_player.play(dur=duration, delay=delay)
        self.amplitude_factor = 1

    def stop(self):
        self._is_playing = False
        self._sound_file_player.stop(wait=self.delay)
        self.amplitude_factor = 0

    @reset_sound_file_attribute
    def jump_to(self, time_in_seconds: float):
        self._sound_file_player.setOffset(time_in_seconds)


class SoundFilePlayerRAM(SoundFilePlayer):
    """Not implemented yet!

    Play sound file from RAM.

    Can fill up RAM, but saves CPU.
    """


class VolumeControl(object):
    pass


class AudioHost(object):
    """Wrapper for pyo.Server and pyo.Mixer.

    Simplifies server API and adds volumes controls.
    """

    # Add slow delay to wait delay, in order to ensure
    # that sound file is faded out already
    SLEEP_TOLERANCE = 0.1

    def __init__(
        self,
        sound_file_tuple: typing.Tuple[SoundFile, ...],
        player: typing.Literal["disk", "ram"] = "disk",
        audio: str = "jack",
        sampling_rate: int = 44100,
        buffer_size: int = 256,
        channel_mapping: typing.Optional[
            typing.Union[ChannelMapping, typing.Dict[int, int]]
        ] = None,
    ):
        assert sound_file_tuple

        self._is_playing = False

        if channel_mapping is None:
            channel_mapping = {
                index: index
                for index in range(
                    max([sound_file.channel_count for sound_file in sound_file_tuple])
                )
            }

        if not isinstance(channel_mapping, ChannelMapping):
            channel_mapping = ChannelMapping(channel_mapping)

        self.sound_file_tuple = self._standardize_sound_file_tuple(sound_file_tuple)

        self.server = pyo.Server(
            sr=sampling_rate,
            nchnls=channel_mapping.maxima_output_channel,
            buffersize=buffer_size,
            duplex=0,  # no input needed!
            audio=audio,
            jackname=walkman.constants.NAME,
        ).boot()

        self.mixer = channel_mapping.to_mixer()
        self.mixer.ctrl()

        sound_file_player_class = {
            "disk": SoundFilePlayerDisk,
            # "ram": SoundFilePlayerRAM,  # NotImplementedYet
        }[player]

        self.sound_file_player = sound_file_player_class(self.sound_file_tuple[0])

        self._add_sound_file_player_to_mixer(channel_mapping)

    def _standardize_sound_file_tuple(
        self, sound_file_tuple: typing.Tuple[SoundFile, ...]
    ) -> typing.Tuple[SoundFile, ...]:
        """Ensure all sound files have the same channel count"""
        maxima_channel_count = max(
            map(lambda sound_file: sound_file.channel_count, sound_file_tuple)
        )
        standardized_sound_file_list = []
        for sound_file in sound_file_tuple:
            standardized_sound_file_list.append(
                sound_file.expand_to(maxima_channel_count)
            )
        return tuple(standardized_sound_file_list)

    def _add_sound_file_player_to_mixer(self, channel_mapping: ChannelMapping):
        for index, input_channel in enumerate(channel_mapping):
            output_channel_tuple = channel_mapping[input_channel]
            if (
                pyo_channel := self.sound_file_player.pyo_object[input_channel]
            ) is not None:
                self.mixer.addInput(index, pyo_channel)
                for output_channel in output_channel_tuple:
                    self.mixer.setAmp(index, output_channel, 1)

        for output_channel in channel_mapping.output_channel_set:
            if mixer_channel := self.mixer[output_channel]:
                mixer_channel[0].out(output_channel)

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def start(self):
        self.server.start()
        self._is_playing = True

    def stop(self):
        self.sound_file_player.amplitude = 0
        time.sleep(self.sound_file_player.delay + self.SLEEP_TOLERANCE)
        self.server.stop()
        self._is_playing = False

    def close(self):
        self.stop()
        [sound_file.close() for sound_file in self.sound_file_tuple]
