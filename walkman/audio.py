import abc
import functools
import time
import typing

import pyo

import walkman

FrameCount = int
DurationInSeconds = float
SamplingRate = int
ChannelCount = int
FileFormat = str
SampleType = str


class ChannelMapping(typing.Dict[int, int]):
    @property
    def output_channel_list(self) -> typing.List[int]:
        return list(self.values())

    @property
    def maxima_output_channel(self) -> int:
        return max(self.output_channel_list) + 1

    def to_mixer(self) -> pyo.Mixer:
        return pyo.Mixer(outs=self.maxima_output_channel)


class SoundFile(object):
    """Initialize a sound file"""

    def __init__(self, sound_file_name: str, path: str, loop: bool = False):
        self.sound_file_name = sound_file_name
        self.path = str(path)
        self.loop = loop

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
        self.amplitude = 1

    def stop(self):
        self._is_playing = False
        self._sound_file_player.stop(wait=self.delay)
        self.amplitude = 0

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

    def __init__(
        self,
        sound_file_tuple: typing.Tuple[SoundFile, ...],
        player: typing.Literal["disk", "ram"] = "disk",
        audio: str = "jack",
        sampling_rate: int = 44100,
        buffer_size: int = 256,
        channel_mapping: typing.Union[ChannelMapping, typing.Dict[int, int]] = {
            index: index for index in range(2)
        },
    ):
        assert sound_file_tuple

        if type(channel_mapping) == dict:
            channel_mapping = ChannelMapping(channel_mapping)

        self.sound_file_tuple = sound_file_tuple

        self.server = pyo.Server(
            sr=sampling_rate,
            nchnls=channel_mapping.maxima_output_channel,
            buffersize=buffer_size,
            duplex=0,  # no input needed!
            audio=audio,
            jackname=walkman.constants.NAME,
        ).boot()

        self.mixer = channel_mapping.to_mixer()

        sound_file_player_class = {
            "disk": SoundFilePlayerDisk,
            # "ram": SoundFilePlayerRAM,  # NotImplementedYet
        }[player]

        self.sound_file_player = sound_file_player_class(sound_file_tuple[0])

        for index, input_channel in enumerate(channel_mapping):
            output_channel = channel_mapping[input_channel]
            if (
                pyo_channel := self.sound_file_player.pyo_object[input_channel]
            ) is not None:
                self.mixer.addInput(index, pyo_channel)
                self.mixer.setAmp(index, output_channel, 1)

        for output_channel in set(channel_mapping.values()):
            if mixer_channel := self.mixer[output_channel]:
                mixer_channel[0].out(output_channel)

    def start(self):
        self.server.start()
        self.sound_file_player.amplitude = 1

    def stop(self):
        self.sound_file_player.amplitude = 0
        time.sleep(self.sound_file_player.delay)
        self.server.stop()
