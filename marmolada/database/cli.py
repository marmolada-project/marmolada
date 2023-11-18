import click

from .setup import setup_db_schema


@click.group()
def database():
    pass


@database.command()
def setup():
    setup_db_schema()
