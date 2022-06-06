import click

import walkman


def start_loop(
    backend: walkman.Backend,
    headless: bool = False,
):
    if not headless:
        gui = walkman.ui.backend_to_gui(backend)
        gui.loop()
    else:
        while True:
            pass


def start_loop_from_toml_file_path(toml_file_path: str, **kwargs):
    backend = walkman.parsers.toml_file_path_to_backend(toml_file_path)
    start_loop(backend, **kwargs)


def start_loop_from_toml_str(toml_file_path: str, **kwargs):
    backend = walkman.parsers.toml_str_to_backend(toml_file_path)
    start_loop(backend, **kwargs)


@click.command()
@click.argument("configuration_file_path")
def main(configuration_file_path: str):
    start_loop_from_toml_file_path(configuration_file_path)
