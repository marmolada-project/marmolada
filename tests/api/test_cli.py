from unittest import mock

from marmolada.api import cli


class TestCLI:
    @mock.patch.dict(cli.config, values={"api": {"host": "HOST", "port": 1234}}, clear=True)
    @mock.patch("marmolada.api.cli.uvicorn")
    def test_serve(self, uvicorn, cli_runner):
        result = cli_runner.invoke(cli.api, "serve")
        assert result.exit_code == 0
        uvicorn.run.assert_called_once_with(
            "marmolada.api.main:app", host=cli.config["api"]["host"], port=cli.config["api"]["port"]
        )
