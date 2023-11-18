from unittest import mock

from marmolada.database import cli


@mock.patch("marmolada.database.cli.setup_db_schema")
def test_setup(setup_db_schema, cli_runner):
    result = cli_runner.invoke(cli.database, "setup")

    assert result.exit_code == 0

    setup_db_schema.assert_called_once_with()
