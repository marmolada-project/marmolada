import click

from .setup import setup_db_schema


@click.group()
def database() -> None:
    pass


@database.command()
def setup() -> None:
    """Create tables from the database model."""
    setup_db_schema()
