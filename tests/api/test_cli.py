from unittest import mock

from marmolada.api.cli import api
from marmolada.core import cli


@api.command("test")
def _test_api():
    pass


class TestCLI:
    def test_api(self, cli_runner):
        result = cli_runner.invoke(cli.cli, ["api", "test"])
        assert result.exit_code == 0

    @mock.patch("marmolada.api.cli.uvicorn")
    def test_serve(self, uvicorn, cli_runner, marmolada_config_files):
        cli_args = [f"--config={cfpath!s}" for cfpath in marmolada_config_files]
        cli_args.extend(["api", "serve"])
        result = cli_runner.invoke(cli.cli, cli_args)
        assert result.exit_code == 0
        uvicorn.run.assert_called_once()
