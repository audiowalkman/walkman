import click

import walkman


@click.command()
@click.option(
    "-h",
    "--headless",
    is_flag=True,
    show_default=True,
    default=False,
    help="Run without GUI",
)
@click.argument("configuration_file_path")
def main(configuration_file_path: str, headless: bool):
    walkman.start_loop_from_jinja2_file_path(configuration_file_path, headless=headless)
