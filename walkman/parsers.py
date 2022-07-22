import typing
import warnings

import jinja2
import tomli

import walkman

CONFIGURE_KEY = "configure"
CONFIGURE_NAME_KEY = "name"
CONFIGURE_AUDIO_KEY = "audio"
CONFIGURE_AUDIO_CHANNEL_COUNT_KEY = "channel_count"
CONFIGURE_MODULE_KEY = "module"

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
    replication_key: int,
    module_name: str,
    replication_configuration: dict,
    configuration: dict,
):
    if replication_key in replication_configuration:
        warnings.warn(
            "Found repeated replication_key '{replication_key}' "
            f"in module '{module_name}'!"
        )
    replication_configuration.update({replication_key: configuration})


def configure_module_block_and_audio_object_to_module_container(
    configure_module_block: dict,
) -> walkman.ModuleContainer:
    module_name_to_replication_configuration_dict = {}
    for module_name, replication_configuration_block in configure_module_block.items():
        replication_configuration = {}
        for replication_key, configuration in replication_configuration_block.items():
            add_replication_instance(
                replication_key, module_name, replication_configuration, configuration
            )
        module_name_to_replication_configuration_dict.update(
            {module_name: replication_configuration}
        )
    return walkman.ModuleContainer.from_module_configuration(
        module_name_to_replication_configuration_dict,
    )


def configure_block_to_global_state_object_tuple(
    configure_block: dict,
) -> typing.Tuple[str, walkman.AudioHost, walkman.ModuleContainer]:
    name = pop_from_dict(configure_block, CONFIGURE_NAME_KEY, "Project")
    audio_block = pop_from_dict(configure_block, CONFIGURE_AUDIO_KEY, {})
    module_block = pop_from_dict(configure_block, CONFIGURE_MODULE_KEY, {})

    warn_not_used_configuration_content(configure_block, "configure")

    audio_host = walkman.AudioHost(**audio_block)
    module_container = configure_module_block_and_audio_object_to_module_container(
        module_block
    )

    return (name, audio_host, module_container)


def cue_block_and_module_container_to_cue_manager(
    cue_block: dict, module_container: walkman.ModuleContainer
) -> walkman.CueManager:
    cue_list = []
    for cue_name, cue_kwargs in cue_block.items():
        module_name_to_replication_configuration = {}
        for module_name, replication_configuration_block in cue_kwargs.items():
            replication_configuration = {}
            for (
                replication_key,
                module_kwargs,
            ) in replication_configuration_block.items():
                add_replication_instance(
                    replication_key,
                    module_name,
                    replication_configuration,
                    module_kwargs,
                )
            module_name_to_replication_configuration.update(
                {module_name: replication_configuration}
            )

        cue = walkman.Cue(
            module_container, cue_name, **module_name_to_replication_configuration
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
    cue_manager = cue_block_and_module_container_to_cue_manager(
        cue_block, global_state_object_tuple[-1]
    )

    backend = walkman.Backend(*global_state_object_tuple, cue_manager)
    return backend


def toml_file_path_to_backend(toml_file_path: str) -> walkman.Backend:
    with open(toml_file_path, "r") as toml_file:
        toml_str = toml_file.read()
    return toml_str_to_backend(toml_str)


def jinja2_file_path_to_backend(jinja2_file_path: str) -> walkman.Backend:
    environment = jinja2.Environment(loader=jinja2.FileSystemLoader("./"))
    template = environment.get_template(jinja2_file_path)
    toml_str = template.render()
    split_jinja2_file_path = jinja2_file_path.split("/")
    jinja2_file_directory_path, jinja2_file_file_path = (
        "/".join(split_jinja2_file_path[:-1]),
        split_jinja2_file_path[-1],
    )
    toml_file_path = (
        f"{jinja2_file_directory_path}/.{jinja2_file_file_path.split('.')[0]}.orc"
    )
    with open(toml_file_path, "w") as toml_file:
        toml_file.write(toml_str)
    walkman.constants.LOGGER.info(
        "WALKMAN converted jinja2 template to toml file"
        f"\n\nPlease check '{toml_file_path}' "
        "for converted file.\n"
    )
    return toml_str_to_backend(toml_str)
