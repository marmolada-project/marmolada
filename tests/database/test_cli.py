from unittest import mock

from marmolada.database import cli
from marmolada.database.cli import migration


@mock.patch.object(cli, "setup_db_schema")
def test_setup(setup_db_schema, cli_runner):
    result = cli_runner.invoke(cli.database, ("setup",))

    assert result.exit_code == 0

    setup_db_schema.assert_called_once_with()


@mock.patch.object(cli, "alembic_migration")
def test_migration_create(alembic_migration, cli_runner):
    result = cli_runner.invoke(migration, ("create", "a", "b", "c"))

    assert result.exit_code == 0

    alembic_migration.create.assert_called_once_with(comment="a b c", autogenerate=True)


@mock.patch.object(cli, "alembic_migration")
def test_migration_db_version(alembic_migration, cli_runner):
    result = cli_runner.invoke(migration, ("db-version",))

    assert result.exit_code == 0

    alembic_migration.db_version.assert_called_once_with()


@mock.patch.object(cli, "alembic_migration")
def test_migration_upgrade(alembic_migration, cli_runner):
    result = cli_runner.invoke(migration, ("upgrade",))

    assert result.exit_code == 0

    alembic_migration.upgrade.assert_called_once_with("head")


@mock.patch.object(cli, "alembic_migration")
def test_migration_downgrade(alembic_migration, cli_runner):
    result = cli_runner.invoke(migration, ("downgrade",))

    assert result.exit_code == 0

    alembic_migration.downgrade.assert_called_once_with("-1")
