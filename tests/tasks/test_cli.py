from unittest import mock

import pytest

from marmolada.tasks import cli


@pytest.mark.parametrize(
    "test_case",
    ("normal", "normal-kbd-interrupt", "normal-process-lookup-error", "illegal-args"),
)
def test_serve(test_case, cli_runner):
    raise_exception = None
    if "kbd-interrupt" in test_case:
        raise_exception = KeyboardInterrupt
    elif "process-lookup-error" in test_case:
        raise_exception = ProcessLookupError

    args = ["serve", "--workers=5"]
    if test_case == "illegal-args":
        args.extend(["--illegal-arg", "some-broker", "some_module"])

    with mock.patch.object(cli, "run_worker") as run_worker:
        if raise_exception:
            run_worker.side_effect = raise_exception
        result = cli_runner.invoke(cli.tasks, args)

    if "illegal-args" not in test_case:
        assert result.exit_code == 0

        run_worker.assert_called_once()
        (worker_args,), kwargs = run_worker.call_args.args, run_worker.call_args.kwargs
        assert not kwargs
        assert isinstance(worker_args, cli.WorkerArgs)
        assert worker_args.workers == 5
    else:
        assert result.exit_code != 0

        run_worker.assert_not_called()
