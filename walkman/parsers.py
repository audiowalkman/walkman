import tomli
import typing

import walkman

CONFIGURE_KEY = "configure"
CONFIGURE_NAME_KEY = "name"
CONFIGURE_AUDIO_KEY = "audio"
CONFIGURE_INPUT_KEY = "input"
CONFIGURE_OUTPUT_KEY = "output"
CONFIGURE_MODULE_KEY = "module"

CUE_KEY = "cue"


def configure_module_block_and_audio_object_to_module_dict(
    configure_module_block: dict,
    audio_host: walkman.AudioHost,
    input_provider: walkman.InputProvider,
    output_provider: walkman.OutputProvider,
) -> walkman.ModuleDict:
    return walkman.ModuleDict.from_audio_objects_and_module_configuration(
        audio_host, input_provider, output_provider, configure_module_block
    )


def configure_block_to_global_state_object_tuple(
    configure_block: dict,
) -> typing.Tuple[
    str,
    walkman.AudioHost,
    walkman.InputProvider,
    walkman.OutputProvider,
    walkman.ModuleDict,
]:
    name = configure_block.get(CONFIGURE_NAME_KEY, "Project")
    audio_block = configure_block.get(CONFIGURE_AUDIO_KEY, {})
    input_block = configure_block.get(CONFIGURE_INPUT_KEY, {})
    output_block = configure_block.get(CONFIGURE_OUTPUT_KEY, {})
    module_block = configure_block.get(CONFIGURE_MODULE_KEY, {})

    audio_host = walkman.AudioHost(**audio_block)
    input_provider = walkman.InputProvider.from_data(**input_block)
    output_provider = walkman.OutputProvider(**output_block)
    module_dict = configure_module_block_and_audio_object_to_module_dict(
        module_block, audio_host, input_provider, output_provider
    )

    return (name, audio_host, input_provider, output_provider, module_dict)


def cue_block_and_module_dict_to_cue_manager(
    cue_block: dict, module_dict: walkman.ModuleDict
) -> walkman.CueManager:
    cue_list = []
    for cue_name, cue_kwargs in cue_block.items():
        cue = walkman.Cue(module_dict, cue_name, **cue_kwargs)
        cue_list.append(cue)

    cue_manager = walkman.CueManager(tuple(cue_list))
    return cue_manager


def toml_str_to_backend(
    toml_str: str = "",
) -> walkman.Backend:
    toml_dictionary = tomli.loads(toml_str)

    configure_block = toml_dictionary.get(CONFIGURE_KEY, {})
    cue_block = toml_dictionary.get(CUE_KEY, {})

    global_state_object_tuple = configure_block_to_global_state_object_tuple(
        configure_block
    )
    cue_manager = cue_block_and_module_dict_to_cue_manager(
        cue_block, global_state_object_tuple[-1]
    )

    backend = walkman.Backend(*global_state_object_tuple, cue_manager)
    return backend


def toml_file_path_to_backend(toml_file_path: str) -> walkman.Backend:
    with open(toml_file_path, "r") as toml_file:
        toml_str = toml_file.read()
    return toml_str_to_backend(toml_str)
