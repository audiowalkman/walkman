"""Parse toml configuration files"""

import tomli

import walkman


SOUNDFILE_TABLE_NAME = "soundfile"
AUDIO_TABLE_NAME = "audio"


class NoSoundFileError(Exception):
    message = "No sound file has been specified in configuration file!"

    def __init__(self):
        super().__init__(self.message)


def toml_str_to_audio_host(
    toml_str: str = "",
) -> walkman.audio.AudioHost:
    toml_dictionary = tomli.loads(toml_str)

    try:
        sound_file_data_list = toml_dictionary[SOUNDFILE_TABLE_NAME]
    except KeyError:
        raise NoSoundFileError()

    sound_file_list = []
    for sound_file_name, sound_file_data in sound_file_data_list.items():
        sound_file_list.append(
            walkman.audio.SoundFile(sound_file_name, **sound_file_data)
        )

    try:
        audio_data_toml = toml_dictionary[AUDIO_TABLE_NAME]
    except KeyError:
        audio_data = {}
    else:
        audio_data = audio_data_toml
    audio_data.update({"sound_file_tuple": tuple(sound_file_list)})

    audio_host = walkman.audio.AudioHost(**audio_data)

    return audio_host


def toml_file_path_to_audio_host(toml_file_path: str) -> walkman.audio.AudioHost:
    with open(toml_file_path, "r") as toml_file:
        toml_str = toml_file.read()
    return toml_str_to_audio_host(toml_str)
