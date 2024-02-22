import click
import uvicorn


@click.group()
def api() -> None:
    pass


@api.command()
def serve() -> None:
    """Serve the web API."""
    uvicorn.run("marmolada.api.main:app")
