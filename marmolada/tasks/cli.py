import json
import os

import click
from taskiq.cli.worker.args import WorkerArgs
from taskiq.cli.worker.run import run_worker

from ..core.configuration import config

ALLOWED_WORKER_ARGS = (
    "--log-level",
    "--log-format",
    "--workers",
    "--max-threadpool-threads",
    "--shutdown-timeout",
    "--max-async-tasks",
    "--max-prefetch",
    "--max-fails",
    "--max-tasks-per-child",
    "--wait-tasks-timeout",
    "--hardkill-count",
    "--use-process-pool",
    "--max-process-pool-processes",
)


@click.group()
def tasks():
    pass


@tasks.command(context_settings={"ignore_unknown_options": True, "help_option_names": []})
@click.argument("worker_args", nargs=-1, type=click.UNPROCESSED)
def serve(worker_args: tuple[str]):
    # Verify argument list
    tripped = False
    for arg in worker_args:
        if arg.startswith("-"):
            arg = arg.split("=", 1)[0]

        if not arg.startswith("-"):
            click.echo(f"Broker or module arguments not accepted: {arg}", err=True)
            tripped = True
        elif arg not in ALLOWED_WORKER_ARGS:
            click.echo(f"Illegal argument: {arg}")
            tripped = True

    if tripped:
        raise click.ClickException("Bailing out.")

    worker_args += ("marmolada.tasks.base:setup_broker_listen",)
    cooked_args = WorkerArgs.from_cli(worker_args)
    os.environ["MARMOLADA_CONFIG_JSON"] = json.dumps(config)
    try:
        run_worker(cooked_args)
    except (KeyboardInterrupt, ProcessLookupError):
        pass
