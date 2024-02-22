import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marmolada.api import base
from marmolada.database import Base
from marmolada.database.model import Import


@pytest.mark.usefixtures("db_test_data")
class TestImports:
    async def test_get_all(self, client: AsyncClient, db_test_data_objs: dict[str, list[Base]]):
        resp = await client.get(f"{base.API_PREFIX}/imports")
        assert resp.status_code == status.HTTP_200_OK
        result = resp.json()
        for import_ in db_test_data_objs["imports"]:
            assert any(o["uuid"] == str(import_.uuid) for o in result["items"])

    async def test_get_one(self, client: AsyncClient, db_test_data_objs: dict[str, list[Base]]):
        import_ = db_test_data_objs["imports"][0]
        resp = await client.get(f"{base.API_PREFIX}/imports/{import_.uuid}")
        assert resp.status_code == status.HTTP_200_OK
        result = resp.json()
        assert result["uuid"] == str(import_.uuid)

    @pytest.mark.parametrize("with_meta", (True, False), ids=("with-meta", "without-meta"))
    async def test_post(self, with_meta: bool, client: AsyncClient, db_session: AsyncSession):
        body = {}
        if with_meta:
            body["meta"] = {"some": "metadata"}

        resp = await client.post(f"{base.API_PREFIX}/imports", json=body)
        assert resp.status_code == status.HTTP_201_CREATED
        result = resp.json()

        async with db_session.begin():
            import_ = (
                await db_session.execute(select(Import).filter_by(uuid=result["uuid"]))
            ).scalar_one()
            assert import_.complete is False

            if with_meta:
                assert import_.meta == {"some": "metadata"}
            else:
                assert import_.meta == {}

    async def test_put(
        self,
        client: AsyncClient,
        db_test_data_objs: dict[str, list[Base]],
        db_session: AsyncSession,
    ):
        import_ = db_test_data_objs["imports"][0]
        resp = await client.put(
            f"{base.API_PREFIX}/imports/{import_.uuid}", json={"complete": False}
        )
        assert resp.status_code == status.HTTP_200_OK
        result = resp.json()
        assert result["complete"] is False

        async with db_session.begin():
            await db_session.refresh(import_)
            assert import_.complete is False
