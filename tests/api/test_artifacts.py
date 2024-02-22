from contextlib import nullcontext
from pathlib import Path
from socket import getfqdn
from unittest import mock
from uuid import UUID

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from marmolada.api import base
from marmolada.database import Base
from marmolada.database.model import Artifact


@pytest.mark.usefixtures("db_test_data")
class TestArtifacts:
    async def test_get_all(self, client: AsyncClient, db_test_data_objs: dict[str, list[Base]]):
        resp = await client.get(f"{base.API_PREFIX}/artifacts")
        assert resp.status_code == status.HTTP_200_OK
        result = resp.json()
        for artifact in db_test_data_objs["artifacts"]:
            assert any(o["uuid"] == str(artifact.uuid) for o in result["items"])

    async def test_get_one(self, client: AsyncClient, db_test_data_objs: dict[str, list[Base]]):
        artifact = db_test_data_objs["artifacts"][0]
        resp = await client.get(f"{base.API_PREFIX}/artifacts/{artifact.uuid}")
        assert resp.status_code == status.HTTP_200_OK
        result = resp.json()
        assert result["uuid"] == str(artifact.uuid)

    @pytest.mark.parametrize(
        "testcase",
        (
            "from-upload-import-exists",
            "from-upload-import-missing",
            "from-local-file-import-exists",
            "from-local-file-import-exists-wrong-uri-scheme",
            "from-local-file-import-exists-wrong-uri-host",
            "from-local-file-import-exists-local-path-missing",
            "from-local-file-import-exists-hardlink-failing",
            "from-local-file-import-missing",
        ),
    )
    async def test_post(
        self,
        testcase: str,
        db_test_data_objs: dict[str, list[Base]],
        tmp_path: Path,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        from_upload = "from-upload" in testcase
        import_exists = "import-missing" not in testcase
        wrong_uri_scheme = "wrong-uri-scheme" in testcase
        wrong_uri_host = "wrong-uri-host" in testcase
        local_path_missing = "local-path-missing" in testcase
        hardlink_failing = "hardlink-failing" in testcase

        patch_context = nullcontext()

        if import_exists:
            import_ = db_test_data_objs["imports"][0]
            import_uuid = import_.uuid
        else:
            import_uuid = UUID(int=0)

        src_file = tmp_path / "an_image.jpg"  # not really a JPEG
        with src_file.open("w") as fp:
            print("Hello!", file=fp)

        if from_upload:
            endpoint = "artifacts"
            kwargs = {
                "params": {"import": str(import_uuid)},
                "files": {"file": (src_file.name, src_file.open("rb"))},
            }
        else:
            endpoint = "artifacts/from-local-file"
            uri_scheme = "file"
            uri_host = getfqdn()
            local_path = src_file.absolute()
            if wrong_uri_scheme:
                uri_scheme = "ut2004"  # This is official.
            if wrong_uri_host:
                uri_host = f"whoops.{uri_host}"
            if local_path_missing:
                local_path = src_file.with_suffix(".foo").absolute()
            if hardlink_failing:
                patch_context = mock.patch("anyio.Path.hardlink_to")

            kwargs = {
                "json": {
                    "import": str(import_uuid),
                    "source_uri": f"{uri_scheme}://{uri_host}{local_path}",
                }
            }

        with patch_context as hardlink_to:
            if hardlink_failing:
                hardlink_to.side_effect = OSError("BOO")
            resp = await client.post(f"{base.API_PREFIX}/{endpoint}", **kwargs)

        result = resp.json()

        if import_exists:
            if wrong_uri_host or wrong_uri_scheme or local_path_missing:
                assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
                assert result["detail"] == "source-uri must point to a local file on the server"
            else:
                assert resp.status_code == status.HTTP_201_CREATED

                async with db_session.begin():
                    await db_session.refresh(import_)
                    artifact = (
                        await db_session.execute(select(Artifact).filter_by(uuid=result["uuid"]))
                    ).scalar_one()
                    assert artifact.import_ is import_

                    assert artifact.full_path.read_text() == "Hello!\n"

                    if from_upload or hardlink_failing:
                        assert artifact.full_path.stat().st_nlink == 1
                    else:
                        assert artifact.full_path.stat().st_nlink == 2
        else:
            assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert result["detail"] == "import not found"
