from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from marmolada.core.configuration import config
from marmolada.database.model import Artifact, ImportBucket

from .common import ModelTestBase


@pytest.fixture(autouse=True)
def artifacts_root_unset_cache():
    with mock.patch.object(Artifact, "artifacts_root", Path(config["artifacts"]["root"])):
        yield


@pytest.mark.marmolada_config({"artifacts": {"root": "doesn't matter"}})
class TestArtifact(ModelTestBase):
    cls = Artifact
    attrs = {"content_type": "image/jpeg", "file_name": "DSC01234.JPG"}

    def _db_obj_get_dependencies(self):
        return {"import_bucket": ImportBucket()}

    async def test_artifacts_root(self, db_session):
        Artifact.artifacts_root = None
        obj = Artifact()
        assert str(obj.artifacts_root) == config["artifacts"]["root"]

    async def test_path_getter(self, db_obj: Artifact):
        assert db_obj._path == str(db_obj.path)
        assert db_obj._path == f"incoming/{db_obj.import_bucket.uuid!s}/{self.attrs['file_name']}"

    @pytest.mark.parametrize("test_type", (str, Path))
    async def test_path_setter(self, test_type: type, db_obj: Artifact, db_session: Session):
        old_path = db_obj.path
        db_obj.path = test_type(f"{old_path}/")
        await db_session.flush()
        assert db_obj.path == old_path

    async def test_path_expression(self, db_obj: Artifact, db_session: Session):
        selected_obj = (
            await db_session.execute(select(Artifact).filter_by(path=db_obj.path))
        ).scalar_one()

        assert selected_obj == db_obj

    async def test_full_path(self, db_obj: Artifact):
        assert Path(config["artifacts"]["root"]) / db_obj.path == db_obj.full_path

    async def test_rename(self, db_obj: Artifact, db_session: Session):
        async with db_session.begin_nested():
            prev_path = db_obj.full_path
            db_obj.data = b"Foo"

        async with db_session.begin_nested():
            db_obj.path = "new/path"
            assert prev_path.exists()
            assert db_obj.full_path.exists()
            assert db_obj.data == b"Foo"

        async with db_session.begin_nested():
            assert not prev_path.exists()
            assert db_obj.full_path.exists()
            assert db_obj.data == b"Foo"
            await db_session.commit()
            assert db_obj.full_path.exists()
            assert not prev_path.exists()

    @pytest.mark.parametrize(
        "testcase",
        (
            "normal",
            "dir-doesnt-exist",
            "dir-not-writable",
            "file-doesnt-exist",
            "delete",
            "rewrite-fails",
            "rollback",
        ),
    )
    async def test_data_descriptor(self, testcase: str, db_obj: Artifact, db_session: Session):
        artifacts_root = Path(config["artifacts"]["root"])

        if testcase == "dir-not-writable":
            artifacts_root_mode = artifacts_root.stat().st_mode
            artifacts_root.chmod(0)
        elif testcase == "dir-doesnt-exist":
            artifacts_root.rmdir()

        if testcase == "dir-not-writable":
            with pytest.raises(OSError):
                db_obj.data = b"Foo"
            with pytest.raises(IOError):
                db_obj.data  # noqa: B018
            artifacts_root.chmod(artifacts_root_mode)
        elif testcase == "file-doesnt-exist":
            with pytest.raises(FileNotFoundError):
                db_obj.data  # noqa: B018
        else:  # testcase in ("normal", "dir-doesnt-exist", "delete", "rewrite-fails", "rollback")
            db_obj.data = b"Foo"
            assert db_obj.data == b"Foo"

        if testcase == "delete":
            del db_obj.data
            with pytest.raises(FileNotFoundError):
                db_obj.data  # noqa: B018
            await db_session.commit()
            assert not db_obj.full_path.exists()
        elif testcase == "rewrite-fails":
            with pytest.raises(FileExistsError):
                db_obj.data = b"Bar"
        elif testcase == "rollback":
            await db_session.rollback()
            assert not db_obj.full_path.exists()
