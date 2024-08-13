import click
import uvicorn

from ..core.configuration import config


@click.group()
def api() -> None:
    pass


@api.command()
def serve() -> None:
    """Serve the web API."""
    uvicorn.run("marmolada.api.main:app", host=config["api"]["host"], port=config["api"]["port"])
