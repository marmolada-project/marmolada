import click
from arq import run_worker

from .base import get_worker_settings


@click.group()
def tasks():
    pass


@tasks.command()
def serve():
    try:
        run_worker(get_worker_settings())
    except KeyboardInterrupt:
        pass
