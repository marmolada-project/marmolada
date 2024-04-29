from unittest import mock

import pytest

from marmolada.tasks import base, main

TEST_CONFIG = {
    "tasks": {
        "arq": {
            "redis_settings": {
                "host": "foo.example.com",
                "port": 63790,
            }
        }
    }
}


@pytest.mark.marmolada_config(TEST_CONFIG)
def test_get_redis_settings():
    redis_settings = base.get_redis_settings()
    assert redis_settings.host == TEST_CONFIG["tasks"]["arq"]["redis_settings"]["host"]
    assert redis_settings.port == TEST_CONFIG["tasks"]["arq"]["redis_settings"]["port"]


async def test_get_taskpool():
    with mock.patch.object(base, "task_pool"), mock.patch.object(
        base, "create_pool"
    ) as create_pool, mock.patch.object(base, "get_redis_settings") as get_redis_settings:
        base.task_pool = None
        get_redis_settings.return_value = redis_settings = object()
        create_pool.return_value = create_pool_retval = object()

        task_pool = await base.get_task_pool()

        assert task_pool is create_pool_retval
        create_pool.assert_awaited_once_with(redis_settings)

        create_pool.reset_mock()

        task_pool = await base.get_task_pool()

        assert task_pool is create_pool_retval
        create_pool.assert_not_awaited()


async def test_startup_task_worker(caplog):
    ctx = object()

    with mock.patch.object(base, "database") as database, caplog.at_level("DEBUG"):
        await base.startup_task_worker(ctx)

    database.init_model.assert_called_once_with()

    assert "Task worker starting up…" in caplog.text
    assert "Task worker started up." in caplog.text


async def test_shutdown_task_worker(caplog):
    ctx = object()

    with caplog.at_level("DEBUG"):
        await base.shutdown_task_worker(ctx)

    assert "Task worker shutting down…" in caplog.text
    assert "Task worker shut down." in caplog.text


def test_get_worker_settings():
    with mock.patch.object(base, "get_redis_settings") as get_redis_settings:
        get_redis_settings.return_value = sentinel = object()

        worker_settings = base.get_worker_settings()

    assert worker_settings.redis_settings is sentinel
    assert main.process_artifact in worker_settings.functions
    assert main.process_import in worker_settings.functions
