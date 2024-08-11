import click

from .migrations import alembic_migration
from .setup import setup_db_schema


@click.group()
def database() -> None:
    pass


@database.command()
def setup() -> None:
    """Create tables from the database model."""
    setup_db_schema()


@database.group()
def migration():
    """Handle database migrations."""


@migration.command("create")
@click.option(
    "--autogenerate/--no-autogenerate",
    default=True,
    help="Autogenerate migration script skeleton (needs to be reviewed/edited).",
)
@click.argument("comment", nargs=-1, required=True)
def migration_create(autogenerate: bool, comment: tuple[str]) -> None:
    """Create a new database schema migration."""
    alembic_migration.create(comment=" ".join(comment), autogenerate=autogenerate)


@migration.command("db-version")
def migration_db_version() -> None:
    """Show the current version of the database schema."""
    alembic_migration.db_version()


@migration.command("upgrade")
@click.argument("version", default="head")
def migration_upgrade(version: str) -> None:
    """Upgrade the database schema."""
    alembic_migration.upgrade(version)


@migration.command("downgrade")
@click.argument("version", default="-1")
def migration_downgrade(version: str) -> None:
    """Downgrade the database schema."""
    alembic_migration.downgrade(version)
