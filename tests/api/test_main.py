from unittest import mock

from httpx import AsyncClient

from marmolada.api import main


class TestApp:
    async def test_lifespan_ctx(self):
        app = object()

        with (
            mock.patch.object(main, "configure_broker") as configure_broker,
            mock.patch.object(main, "init_model") as init_model,
        ):
            configure_broker.return_value = broker = mock.AsyncMock()
            broker.is_worker_process = False

            async with main.lifespan(app):
                broker.startup.assert_awaited_once_with()
                broker.shutdown.assert_not_awaited()
                init_model.assert_called_once_with()

            broker.shutdown.assert_awaited_once_with()

    async def test_openapi_schema(self, client: AsyncClient):
        response = await client.get("/openapi.json")

        assert response.status_code == 200

        result = response.json()
        assert {"openapi", "info", "paths", "components"} <= set(result)
