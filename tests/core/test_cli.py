from unittest import mock

import pytest

from marmolada.core import cli


@cli.cli.command("test")
def _test_cli():
    pass


class TestCLI:
    @pytest.mark.parametrize("testcase", ("without-config", "with-config", "with-missing-config"))
    @mock.patch("marmolada.core.configuration.read_configuration")
    def test_init_config(self, read_configuration, testcase, tmp_path, cli_runner):
        args = ("test",)
        match testcase:
            case "with-config":
                args = ("-c", "/dev/null", *args)
            case "with-missing-config":
                args = ("-c", str(tmp_path / "this doesn’t exist"), *args)
                read_configuration.side_effect = FileNotFoundError

        result = cli_runner.invoke(cli.cli, args)

        match testcase:
            case "without-config":
                assert result.exit_code == 0
                assert read_configuration.call_count == 2
                read_configuration.assert_has_calls(
                    (
                        mock.call(cli.DEFAULT_CONFIG_FILE, clear=True, validate=False),
                        mock.call(clear=False, validate=True),
                    )
                )
            case "with-config":
                assert result.exit_code == 0
                assert read_configuration.call_count == 2
                read_configuration.assert_has_calls(
                    (
                        mock.call("/dev/null", clear=True, validate=False),
                        mock.call(clear=False, validate=True),
                    )
                )
            case "with-missing-config":
                assert result.exit_code != 0
                assert isinstance(result.exception, FileNotFoundError)
                read_configuration.assert_called_once_with(
                    str(tmp_path / "this doesn’t exist"), clear=True, validate=False
                )
