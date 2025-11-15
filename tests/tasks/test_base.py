import json
from unittest import mock

import pytest

from marmolada.tasks import base

TEST_CONFIG = {
    "tasks": {
        "taskiq": {
            "broker_url": "redis://foo.example.com:63790",
        }
    }
}


@pytest.mark.marmolada_config(TEST_CONFIG)
def test_configure_broker():
    with (
        mock.patch.object(base, "RedisStreamBroker") as RedisStreamBroker,
        mock.patch.object(base, "async_shared_broker") as async_shared_broker,
    ):
        RedisStreamBroker.return_value = sentinel = object()
        assert base.configure_broker() is sentinel
        RedisStreamBroker.assert_called_once_with(TEST_CONFIG["tasks"]["taskiq"]["broker_url"])
        async_shared_broker.default_broker.assert_called_once_with(sentinel)


@pytest.mark.marmolada_config(TEST_CONFIG)
def test_setup_broker_listen():
    PASSED_CONFIG = {
        "tasks": {
            "taskiq": {
                "broker_url": "redis://bar.example.com:1234",
            }
        }
    }

    with (
        mock.patch.dict("os.environ", clear=True, MARMOLADA_CONFIG_JSON=json.dumps(PASSED_CONFIG)),
        mock.patch.object(base, "config") as config,
        mock.patch.object(base, "configure_broker") as configure_broker,
        mock.patch.object(base, "database") as database,
        mock.patch.object(base, "main") as base_main,
        mock.patch.object(base, "TaskPluginManager") as TaskPluginManager,
    ):
        configure_broker.return_value = expected_configured_broker = object()
        TaskPluginManager.return_value = task_plugin_mgr = mock.Mock()

        configured_broker = base.setup_broker_listen()

        assert configured_broker is expected_configured_broker
        assert config.mock_calls == [
            mock.call.clear(),
            mock.call.update(PASSED_CONFIG),
        ]
        configure_broker.assert_called_once_with()
        database.init_model.assert_called_once_with()
        assert base_main.plugin_mgr is task_plugin_mgr
        task_plugin_mgr.discover_plugins.assert_called_once_with()
