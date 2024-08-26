import logging
from typing import TYPE_CHECKING

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

if TYPE_CHECKING:
    from arq.typing import WorkerSettingsType

from .. import database
from ..core.configuration import config
from . import main
from .plugins import TaskPluginManager
from .typing import Context

log = logging.getLogger(__name__)
task_pool: ArqRedis | None = None


def get_redis_settings() -> RedisSettings:
    redis_settings = config["tasks"]["arq"]["redis_settings"] or {}
    return RedisSettings(**redis_settings)


async def get_task_pool() -> ArqRedis:
    global task_pool

    if not task_pool:
        task_pool = await create_pool(get_redis_settings())

    return task_pool


async def startup_task_worker(ctx: Context) -> None:
    log.info("Task worker starting up…")

    database.init_model()
    main.plugin_mgr = TaskPluginManager()
    main.plugin_mgr.discover_plugins()

    log.info("Task worker started up.")


async def shutdown_task_worker(ctx: Context) -> None:
    log.info("Task worker shutting down…")

    ...

    log.info("Task worker shut down.")


def get_worker_settings() -> "WorkerSettingsType":
    class WorkerSettings:
        redis_settings = get_redis_settings()

        functions = (
            main.process_artifact,
            main.process_import,
        )

        on_startup = startup_task_worker
        on_shutdown = shutdown_task_worker

    return WorkerSettings
