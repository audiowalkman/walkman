import click

import walkman


@click.command()
@click.argument("configuration_file_path")
def main(configuration_file_path: str):
    walkman.boot.start_loop_from_toml_file_path(configuration_file_path)
