import tomli
import typing
import warnings

import walkman

CONFIGURE_KEY = "configure"
CONFIGURE_NAME_KEY = "name"
CONFIGURE_AUDIO_KEY = "audio"
CONFIGURE_INPUT_KEY = "input"
CONFIGURE_OUTPUT_KEY = "output"
CONFIGURE_MODULE_KEY = "module"
CONFIGURE_MODULE_REPLICATION_COUNT_KEY = "replication_count"

CUE_KEY = "cue"


def pop_from_dict(dict_to_pop_from: dict, name: str, fallback_value: typing.Any = None):
    try:
        value = dict_to_pop_from[name]
    except KeyError:
        value = fallback_value
    else:
        del dict_to_pop_from[name]
    return value


class UnusedSpecificationWarning(Warning):
    pass


def warn_not_used_configuration_content(toml_block: dict, block_name: str):
    if toml_block:
        formatted_toml_block = "\t>>> ".join(str(toml_block).splitlines(True))
        warnings.warn(
            "WALKMAN ignored the following invalid specifications "
            f"in '{block_name.upper()}':\n{formatted_toml_block}",
            UnusedSpecificationWarning,
        )


def add_replication_instance(
    replication_index: int,
    module_name: str,
    replication_configuration: dict,
    configuration: dict,
):
    try:
        replication_index = int(replication_index)
    except ValueError:
        warnings.warn(
            f"Found invalid replication index '{replication_index}'"
            f" in module '{module_name}'. Only integers are allowed!"
        )
    else:
        replication_configuration.update({replication_index: configuration})


def configure_module_block_and_audio_object_to_module_dict(
    configure_module_block: dict,
    audio_host: walkman.AudioHost,
    input_provider: walkman.InputProvider,
    output_provider: walkman.OutputProvider,
) -> walkman.ModuleDict:
    module_name_to_replication_configuration_dict = {}
    for module_name, replication_configuration_block in configure_module_block.items():
        replication_count = pop_from_dict(
            replication_configuration_block,
            CONFIGURE_MODULE_REPLICATION_COUNT_KEY,
            None,
        )
        replication_configuration = {}
        for replication_index, configuration in replication_configuration_block.items():
            add_replication_instance(
                replication_index, module_name, replication_configuration, configuration
            )
        if replication_count is not None:
            for replication_index in range(int(replication_count)):
                if replication_index not in replication_configuration:
                    replication_configuration.update({replication_index: {}})
        module_name_to_replication_configuration_dict.update(
            {module_name: replication_configuration}
        )
    return walkman.ModuleDict.from_audio_objects_and_module_configuration(
        audio_host,
        input_provider,
        output_provider,
        module_name_to_replication_configuration_dict,
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
    name = pop_from_dict(configure_block, CONFIGURE_NAME_KEY, "Project")
    audio_block = pop_from_dict(configure_block, CONFIGURE_AUDIO_KEY, {})
    input_block = pop_from_dict(configure_block, CONFIGURE_INPUT_KEY, {})
    output_block = pop_from_dict(configure_block, CONFIGURE_OUTPUT_KEY, {})
    module_block = pop_from_dict(configure_block, CONFIGURE_MODULE_KEY, {})

    warn_not_used_configuration_content(configure_block, "configure")

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
        module_name_to_replication_configuration = {}
        for module_name, replication_configuration_block in cue_kwargs.items():
            replication_configuration = {}
            for (
                replication_index,
                module_kwargs,
            ) in replication_configuration_block.items():
                add_replication_instance(
                    replication_index,
                    module_name,
                    replication_configuration,
                    module_kwargs,
                )
            module_name_to_replication_configuration.update(
                {module_name: replication_configuration}
            )

        cue = walkman.Cue(
            module_dict, cue_name, **module_name_to_replication_configuration
        )
        cue_list.append(cue)

    cue_manager = walkman.CueManager(tuple(cue_list))
    return cue_manager


def toml_str_to_backend(
    toml_str: str = "",
) -> walkman.Backend:
    toml_dictionary = tomli.loads(toml_str)

    configure_block = pop_from_dict(toml_dictionary, CONFIGURE_KEY, {})
    cue_block = pop_from_dict(toml_dictionary, CUE_KEY, {})
    warn_not_used_configuration_content(toml_dictionary, "global")

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
