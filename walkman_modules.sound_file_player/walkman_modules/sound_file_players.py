from __future__ import annotations

import dataclasses
import functools
import tempfile
import time
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


class NotEnoughChannelWarning(Warning):
    """Hint if user given soundfiles don't have enough channels"""


class SoundFile(object):
    """Initialize a sound file"""

    def __init__(
        self,
        path: str,
        # In case SoundFile is available as a temporary file (because
        # channels have been added) we have to pass the
        # temporary_file to the object in order to avoid that
        # the garbage collector closes the file.
        temporary_file: typing.Optional[tempfile.NamedTemporaryFile] = None,
    ):
        self.path = str(path)
        self.temporary_file = temporary_file

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
                f"SoundFile '{self.path}' misses {difference} channels. "
                f"{walkman.constants.NAME} automatically added {difference}"
                " silent channels.",
                NotEnoughChannelWarning,
            )
            temporary_file = tempfile.NamedTemporaryFile()
            new_path = temporary_file.name
            self._expand_sound_file(new_path, difference)
            expanded_sound_file = type(self)(
                path=new_path,
                temporary_file=temporary_file,
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


def reset_sound_file_attribute(method_to_wrap: typing.Callable) -> typing.Callable:
    def wrapper(self, *args, **kwargs):
        if is_playing := self.is_playing:
            self.stop()
        return_value = method_to_wrap(self, *args, **kwargs)
        if is_playing:
            self.play()
        return return_value

    return wrapper


class TooSmallChannelCountWarning(Warning):
    pass


@dataclasses.dataclass
class SoundFilePlayer(walkman.ModuleWithDecibel):
    """Play sound file."""

    channel_count: int = 1
    # If set to 'disk': Can be expensive for CPU, but saves RAM.
    mode: typing.Union[typing.Literal["ram"], typing.Literal["disk"]] = "disk"
    path_to_sound_file_dict: dict = dataclasses.field(default_factory=lambda: {})

    _current_time: float = 0
    _start_time: float = 0

    def setup_pyo_object(self):
        super().setup_pyo_object()

        temporary_file = tempfile.NamedTemporaryFile()
        temporary_file_path = temporary_file.name
        self._temporary_file = temporary_file

        base_list = [0 for _ in range(self.channel_count)]
        sound_file_content = np.array([base_list, base_list], dtype="int16")
        soundfile.write(temporary_file_path, sound_file_content, 44100, format="wav")

        self._sound_file_player = pyo.SfPlayer(
            temporary_file_path, mul=self._decibel_signal_to, interp=1
        )
        self._sound_file_player.stop()

        self._sound_file = SoundFile(temporary_file_path)
        self.path_to_sound_file_dict.update({temporary_file_path: self._sound_file})

    def _jump_to(self, time_in_seconds: float):
        self._sound_file_player.setOffset(time_in_seconds)

    def _play(self, duration: float = 0, delay: float = 0):
        super()._play(duration, delay)
        self._jump_to(self._current_time)
        self._start_time = time.time()
        self._sound_file_player.play(dur=duration, delay=delay)

    def _stop(self, wait: float = 0):
        super()._stop(wait)
        self._current_time = min(
            ((time.time() - self._start_time) + self._current_time, self.duration)
        )
        self._sound_file_player.stop(wait=wait)

    def _initialise(self, path: str, decibel: walkman.Parameter = -6, loop: bool = False):  # type: ignore
        super()._initialise(decibel=decibel)

        self.loop = loop

        try:
            sound_file = self.path_to_sound_file_dict[path]
        except KeyError:
            sound_file = SoundFile(path)
            channel_count = sound_file.channel_count
            difference = self.channel_count - channel_count
            if difference > 0:
                sound_file = sound_file.expand_to(self.channel_count)
            elif difference < 0:
                warnings.warn(
                    f"Can't load sound_file with path = {path}. "
                    "Global channel_count for SoundFilePlayer "
                    f"module is {abs(difference)} channel(s) too small ("
                    f"Global channel count: {self.channel_count}; SoundFile "
                    f"channel count: {channel_count}).",
                    TooSmallChannelCountWarning,
                )
                return
            self.path_to_sound_file_dict.update({path: sound_file})

        self.sound_file = sound_file

    @property
    def _pyo_object(self) -> pyo.PyoObject:
        return self._sound_file_player

    @property
    def is_playing(self) -> bool:
        is_playing = self._is_playing
        sound_file_player = self._sound_file_player
        if is_playing and not sound_file_player.isPlaying():
            self._stop()
            self._is_playing = is_playing = False
        return is_playing

    @property
    def sound_file(self) -> SoundFile:
        return self._sound_file

    @sound_file.setter
    @reset_sound_file_attribute
    def sound_file(self, sound_file: SoundFile):
        sound_file_player = self._sound_file_player
        if sound_file_player.path != sound_file.path:
            sound_file_player.setPath(sound_file.path)
        self._sound_file = sound_file

    @property
    def loop(self) -> bool:
        return self._loop

    @loop.setter
    @reset_sound_file_attribute
    def loop(self, loop: bool):
        self._loop = loop
        sound_file_player = self._sound_file_player
        sound_file_player.setLoop(loop)

    @property
    def duration(self) -> float:
        return self.sound_file.duration_in_seconds

    @reset_sound_file_attribute
    def jump_to(self, time_in_seconds: float):
        self._current_time = time_in_seconds
        self._jump_to(time_in_seconds)

    def close(self):
        for sound_file in self.path_to_sound_file_dict.values():
            sound_file.close()
