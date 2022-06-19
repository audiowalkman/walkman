"""Boot walkman loop (with or without UI)"""

import walkman


__all__ = ("start_loop_from_jinja2_file_path", "start_loop_from_toml_str")


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


def start_loop_from_jinja2_file_path(jinja2_file_path: str, **kwargs):
    backend = walkman.parsers.jinja2_file_path_to_backend(jinja2_file_path)
    start_loop(backend, **kwargs)


def start_loop_from_toml_str(toml_file_path: str, **kwargs):
    backend = walkman.parsers.toml_str_to_backend(toml_file_path)
    start_loop(backend, **kwargs)
