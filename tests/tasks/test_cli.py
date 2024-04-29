from unittest import mock

import pytest

from marmolada.tasks import cli


@pytest.mark.parametrize("with_kbd_interrupt", (False, True), ids=("normal", "kbd-interrupt"))
def test_serve(with_kbd_interrupt, cli_runner):
    with mock.patch.object(cli, "run_worker") as run_worker, mock.patch.object(
        cli, "get_worker_settings"
    ) as get_worker_settings:
        get_worker_settings.return_value = sentinel = object()
        if with_kbd_interrupt:
            run_worker.side_effect = KeyboardInterrupt
        result = cli_runner.invoke(cli.tasks, "serve")

    assert result.exit_code == 0

    get_worker_settings.assert_called_once_with()
    run_worker.assert_called_once_with(sentinel)
