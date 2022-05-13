import walkman


def start_loop(
    audio_host: walkman.audio.AudioHost,
    headless: bool = False,
):
    if not headless:
        gui = walkman.ui.audio_host_to_gui(audio_host)
        gui.loop()
    else:
        while True:
            pass


def start_loop_from_toml_file_path(toml_file_path: str, **kwargs):
    audio_host = walkman.configurations.toml_file_path_to_audio_host(toml_file_path)
    start_loop(audio_host, **kwargs)


def start_loop_from_toml_str(toml_file_path: str, **kwargs):
    audio_host = walkman.configurations.toml_str_to_audio_host(toml_file_path)
    start_loop(audio_host, **kwargs)
