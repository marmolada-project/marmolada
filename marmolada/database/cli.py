import asyncio

import click

from .setup import setup_db_schema


@click.group()
def database():
    pass


@database.command()
def setup():
    asyncio.run(setup_db_schema())
