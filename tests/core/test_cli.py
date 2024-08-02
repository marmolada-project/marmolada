from contextlib import nullcontext
from unittest import mock

import pytest

from marmolada.core import cli


@pytest.fixture(autouse=True)
def dont_read_system_config_file(tmp_path):
    with mock.patch.object(cli, "DEFAULT_CONFIG_FILE"):
        cli.DEFAULT_CONFIG_FILE = tmp_path / "marmolada-config.yml"
        cli.DEFAULT_CONFIG_FILE.touch()
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
        mock_config_file = nullcontext()
        match testcase:
            case "without-config":
                mock_config_file = mock.patch.object(cli, "DEFAULT_CONFIG_FILE")
            case "with-default-config":
                pass
            case "with-config":
                args = ("-c", "/dev/null", *args)
            case "with-missing-config":
                args = ("-c", str(tmp_path / "this doesn’t exist"), *args)
                read_configuration.side_effect = FileNotFoundError

        with mock_config_file as mocked_config_file:
            if isinstance(mocked_config_file, mock.Mock):
                mocked_config_file.exists.return_value = False
            result = cli_runner.invoke(cli.cli, args)

        match testcase:
            case "without-config":
                assert result.exit_code == 0
                read_configuration.assert_called_once_with()
            case "with-default-config":
                assert result.exit_code == 0
                read_configuration.assert_called_once_with(cli.DEFAULT_CONFIG_FILE)
            case "with-config":
                assert result.exit_code == 0
                read_configuration.assert_called_once_with("/dev/null")
            case "with-missing-config":
                assert result.exit_code != 0
                read_configuration.assert_not_called()
