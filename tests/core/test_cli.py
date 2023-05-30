from unittest import mock

import pytest

from marmolada.core import cli


@pytest.fixture(autouse=True)
def dont_read_system_config_file(tmp_path):
    with mock.patch.object(cli, "DEFAULT_CONFIG_FILE"):
        cli.DEFAULT_CONFIG_FILE = str(tmp_path / "marmolada-config.yml")
        yield


@cli.cli.command("test")
def _test_cli():
    pass


class TestCLI:
    @pytest.mark.parametrize(
        "testcase", ("without-config", "with-default-config", "with-config", "with-missing-config")
    )
    @mock.patch("marmolada.core.configuration.read_configuration")
    def test_init_config(self, read_configuration, testcase, tmp_path, cli_runner):
        args = ("test",)
        match testcase:
            case "without-config":
                read_configuration.side_effect = FileNotFoundError
            case "with-default-config":
                pass
            case "with-config":
                args = ("-c", "/dev/null", *args)
            case "with-missing-config":
                args = ("-c", str(tmp_path / "this doesn’t exist"), *args)
                read_configuration.side_effect = FileNotFoundError

        result = cli_runner.invoke(cli.cli, args)

        match testcase:
            case "without-config" | "with-default-config":
                assert result.exit_code == 0
                read_configuration.assert_called_once_with(
                    cli.DEFAULT_CONFIG_FILE, clear=True, validate=True
                )
            case "with-config":
                assert result.exit_code == 0
                read_configuration.assert_called_once_with("/dev/null", clear=True, validate=True)
            case "with-missing-config":
                assert result.exit_code != 0
                read_configuration.assert_not_called()
