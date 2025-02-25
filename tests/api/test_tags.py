from unittest import mock

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from marmolada.api import base
from marmolada.database import Base
from marmolada.database.model import Tag, TagLabel


@pytest.mark.usefixtures("db_test_data")
class TestTags:
    async def test_get_all(self, client: AsyncClient, db_test_data_objs: dict[str, list[Base]]):
        resp = await client.get(f"{base.API_PREFIX}/tags")
        assert resp.status_code == status.HTTP_200_OK
        result = resp.json()
        for tag in db_test_data_objs["tags"]:
            assert any(o["uuid"] == str(tag.uuid) for o in result["items"])

    async def test_get_one(self, client: AsyncClient, db_test_data_objs: dict[str, list[Base]]):
        tag = db_test_data_objs["tags"][0]
        resp = await client.get(f"{base.API_PREFIX}/tags/{tag.uuid}")
        assert resp.status_code == status.HTTP_200_OK
        result = resp.json()
        assert result["uuid"] == str(tag.uuid)

    @pytest.mark.parametrize(
        "with_parents, tags_missing",
        (
            pytest.param(True, False, id="with-parents"),
            pytest.param(True, True, id="with-parents-missing"),
            pytest.param(False, False, id="without-parents"),
        ),
    )
    async def test_post(
        self,
        with_parents: bool,
        tags_missing: bool,
        db_test_data_objs: dict[str, list[Base]],
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        body = {
            "labels": [
                "simple-label",
                {"label": "qualified-label", "languages": ["en", "en_US"]},
            ],
        }
        if with_parents:
            parent_tag = db_test_data_objs["tags"][0]
            body["parents"] = [str(parent_tag.uuid)]

        if tags_missing:
            async with db_session.begin():
                await db_session.execute(delete(Tag))

        resp = await client.post(f"{base.API_PREFIX}/tags", json=body)
        if with_parents and tags_missing:
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            return

        assert resp.status_code == status.HTTP_201_CREATED
        result = resp.json()

        async with db_session.begin():
            tag = (
                (await db_session.execute(select(Tag).filter_by(uuid=result["uuid"])))
                .unique()
                .scalar_one()
            )

            parents = await tag.awaitable_attrs.parents
            if with_parents:
                assert parents == {parent_tag}
            else:
                assert parents == set()

    @pytest.mark.parametrize(
        (
            "with_parents, with_children, other_tags_missing, tag_missing, with_labels,"
            + " with_cyclic_error"
        ),
        (
            pytest.param(True, False, False, False, True, False, id="with-parents"),
            pytest.param(True, False, False, False, True, True, id="with-parents-cyclic-error"),
            pytest.param(True, False, True, False, True, False, id="with-parents-missing"),
            pytest.param(False, True, False, False, True, False, id="with-children"),
            pytest.param(False, True, False, False, True, True, id="with-children-cyclic-error"),
            pytest.param(False, True, True, False, True, False, id="with-children-missing"),
            pytest.param(False, False, False, True, True, False, id="with-tag-not-found"),
            pytest.param(False, False, False, False, False, False, id="without-labels"),
        ),
    )
    async def test_put(
        self,
        with_parents: bool,
        with_children: bool,
        other_tags_missing: bool,
        tag_missing: bool,
        with_labels: bool,
        with_cyclic_error: bool,
        client: AsyncClient,
        db_test_data_objs: dict[str, list[Base]],
        db_session: AsyncSession,
        mock_task_pool: mock.AsyncMock,
    ):
        parent_tag, tag, child_tag = db_test_data_objs["tags"][:3]

        body = {}
        if with_parents:
            body["parents"] = [str(parent_tag.uuid)]
            if with_cyclic_error:
                body["parents"].append(str(tag.uuid))
        if with_children:
            body["children"] = [str(child_tag.uuid)]
            if with_cyclic_error:
                body["children"].append(str(tag.uuid))
        if with_labels:
            body["labels"] = [
                "simple-label",
                {"label": "qualified-label", "languages": ["en", "en_US"]},
            ]

        async with db_session.begin():
            if other_tags_missing or tag_missing:
                delete_query = delete(Tag)
                if not tag_missing and other_tags_missing:
                    delete_query = delete_query.filter(Tag.id != tag.id)
                elif not other_tags_missing and tag_missing:
                    delete_query = delete_query.filter(Tag.id == tag.id)
                await db_session.execute(delete_query)

            if not tag_missing and with_labels:
                # Ensure one label exists already
                tag_label = TagLabel(tag_id=tag.id, label="simple-label")
                db_session.add(tag_label)

        resp = await client.put(f"{base.API_PREFIX}/tags/{tag.uuid}", json=body)
        result = resp.json()

        if tag_missing:
            assert resp.status_code == status.HTTP_404_NOT_FOUND
            return

        if (with_parents or with_children) and (other_tags_missing or with_cyclic_error):
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            if other_tags_missing:
                if with_parents:
                    assert f"Failure looking up parents: {parent_tag.uuid}" in result["detail"]
                if with_children:
                    assert f"Failure looking up children: {child_tag.uuid}" in result["detail"]
            if with_cyclic_error:
                if with_parents:
                    assert f"{tag.uuid} can’t be made parent of itself." in result["detail"]
                if with_children:
                    assert f"{tag.uuid} can’t be made child of itself." in result["detail"]
            return

        assert resp.status_code == status.HTTP_200_OK

        async with db_session.begin():
            tag = (
                (await db_session.execute(select(Tag).filter_by(uuid=result["uuid"])))
                .unique()
                .scalar_one()
            )

            parents = await tag.awaitable_attrs.parents
            if with_parents:
                assert parents == {parent_tag}
            else:
                assert parents == set()

            children = await tag.awaitable_attrs.children
            if with_children:
                assert children == {child_tag}
            else:
                assert children == set()
