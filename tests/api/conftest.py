from collections.abc import Iterator

import pytest
from httpx import ASGITransport, AsyncClient

from marmolada.api.main import app


@pytest.fixture
async def client() -> Iterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://marmolada.example.net"
    ) as client:
        yield client
