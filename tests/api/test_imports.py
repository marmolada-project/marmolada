from unittest import mock

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

    @pytest.mark.parametrize(
        "testcase", ("success-happy-path", "success-noop", "failure-cant-uncomplete")
    )
    async def test_put(
        self,
        testcase: str,
        client: AsyncClient,
        db_test_data_objs: dict[str, list[Base]],
        db_session: AsyncSession,
        mock_task_pool: mock.AsyncMock,
    ):
        import_ = db_test_data_objs["imports"][0]

        success = "success" in testcase
        noop = "noop" in testcase
        cant_uncomplete = "cant-uncomplete" in testcase
        expected_import_complete = (success and not noop) or cant_uncomplete

        desired_complete = False
        if success:
            if not noop:
                # Import needs to be incomplete to set it to complete
                desired_complete = True
            async with db_session.begin():
                import_._complete = False

        resp = await client.put(
            f"{base.API_PREFIX}/imports/{import_.uuid}", json={"complete": desired_complete}
        )

        result = resp.json()
        if success:
            assert resp.status_code == status.HTTP_200_OK
            assert result["complete"] is desired_complete
            if noop:
                mock_task_pool.enqueue_job.assert_not_awaited()
            else:
                mock_task_pool.enqueue_job.assert_awaited_once_with("process_import", import_.uuid)
        else:
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
            assert result["detail"] == "Completed import can’t be set incomplete."
            mock_task_pool.enqueue_job.assert_not_awaited()

        async with db_session.begin():
            await db_session.refresh(import_)
            assert import_.complete is expected_import_complete
