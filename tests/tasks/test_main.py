from unittest import mock
from uuid import uuid1

import pytest

from marmolada.tasks import main

TEST_CTX = {}


@pytest.fixture
def plugin_mgr():
    with mock.patch.object(main, "plugin_mgr", new_callable=mock.AsyncMock) as plugin_mgr:
        yield plugin_mgr


async def test_process_artifact(plugin_mgr):
    uuid = uuid1()

    await main.process_artifact(TEST_CTX, uuid)

    plugin_mgr.process_scope.assert_called_once_with(scope="artifact", uuid=uuid)


async def test_process_import(plugin_mgr):
    uuid = uuid1()

    await main.process_import(TEST_CTX, uuid)

    plugin_mgr.process_scope.assert_called_once_with(scope="import", uuid=uuid)
