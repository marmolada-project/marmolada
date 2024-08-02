import logging
from importlib.metadata import entry_points
from pathlib import Path

import click
import click_plugins

from . import configuration

DEFAULT_CONFIG_FILE = Path("/etc/marmolada/config.yaml")


@click_plugins.with_plugins(entry_points(group="marmolada.cli"))
@click.group(name="marmolada")
@click.option(
    "config_paths",
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    multiple=True,
    help="Read option defaults from the specified YAML file(s).",
)
@click.option("--debug/--no-debug", default=False, help="Run with debugging enabled")
@click.pass_context
def cli(ctx: click.Context, config_paths: tuple[Path], debug: bool):
    """Marmolada - a media object store."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug

    if not config_paths and DEFAULT_CONFIG_FILE.exists():
        config_paths = (DEFAULT_CONFIG_FILE,)

    configuration.read_configuration(*config_paths)

    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
