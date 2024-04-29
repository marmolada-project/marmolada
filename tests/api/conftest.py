from collections.abc import Iterator
from unittest import mock

import pytest
from httpx import ASGITransport, AsyncClient

from marmolada.api.main import app
from marmolada.tasks.base import get_task_pool


@pytest.fixture
async def client() -> Iterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://marmolada.example.net"
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def reset_dependency_overrides():
    yield

    app.dependency_overrides = {}


@pytest.fixture
def mock_task_pool(reset_dependency_overrides):
    get_task_pool_mock = mock.AsyncMock()

    app.dependency_overrides[get_task_pool] = lambda: get_task_pool_mock

    return get_task_pool_mock
