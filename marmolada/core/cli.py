from importlib.metadata import entry_points

import click
import click_plugins

from . import configuration

DEFAULT_CONFIG_FILE = "/etc/marmolada/config.yaml"


def init_config(ctx, param, filename):
    ctx.ensure_object(dict)
    try:
        configuration.read_configuration(
            filename, clear=ctx.obj.get("clear_config", True), validate=False
        )
    except FileNotFoundError:
        if filename is not DEFAULT_CONFIG_FILE:
            raise
    ctx.obj["clear_config"] = False


@click_plugins.with_plugins(entry_points(group="marmolada.cli"))
@click.group(name="marmolada")
@click.option(
    "-c",
    "--config",
    type=click.Path(dir_okay=False),
    default=DEFAULT_CONFIG_FILE,
    callback=init_config,
    is_eager=True,
    expose_value=False,
    help="Read option defaults from the specified YAML file.",
    show_default=True,
)
@click.option("--debug/--no-debug", default=False, help="Run with debugging enabled")
@click.pass_context
def cli(ctx: click.Context, debug: bool):
    """Marmolada - a media object store."""
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    configuration.read_configuration(clear=False, validate=True)
