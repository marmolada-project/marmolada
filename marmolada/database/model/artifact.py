import errno
import logging
import os
import pathlib
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar

import magic
from anyio import Path as AsyncPath
from sqlalchemy import ForeignKey, event
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    Mapped,
    QueryableAttribute,
    Session,
    mapped_column,
    object_session,
    relationship,
)
from sqlalchemy.sql import SQLColumnExpression

from ...core.configuration import config
from .. import Base
from ..mixins import BigIntPrimaryKey, Creatable, Updatable, UuidAltKey

if TYPE_CHECKING:
    from .task import ArtifactTask, ImportTask

log = logging.getLogger(__name__)
mime = magic.open(magic.MAGIC_MIME_TYPE)
mime.load()


class Import(Base, BigIntPrimaryKey, UuidAltKey, Creatable, Updatable):
    __tablename__ = "imports"

    meta: Mapped[dict[str, Any]] = mapped_column(default=dict)
    _complete: Mapped[bool] = mapped_column("complete", default=False)
    artifacts: Mapped[set["Artifact"]] = relationship(back_populates="import_")

    tasks: Mapped[set["ImportTask"]] = relationship(back_populates="import_")

    @hybrid_property
    def complete(self) -> bool:
        return self._complete

    @complete.setter
    def complete(self, value: bool) -> None:
        if self._complete and not value:
            raise ValueError("Completed import can’t be set incomplete.")
        self._complete = value

    @complete.expression
    def complete(cls) -> QueryableAttribute:
        return cls._complete


def _artifact_path_default(context: DefaultExecutionContext) -> str:
    params = context.get_current_parameters()
    uuid = params["uuid"]
    import_id = params["import_id"]
    file_name = params["file_name"]
    return f"incoming/import-{import_id}-artifact-{uuid}-{file_name}"


class Artifact(Base, BigIntPrimaryKey, UuidAltKey, Creatable, Updatable):
    __tablename__ = "artifacts"

    artifacts_root: ClassVar[pathlib.Path | None] = None

    _sessions_added_files: ClassVar = defaultdict(set)
    _sessions_removed_files: ClassVar = defaultdict(set)

    content_type: Mapped[str | None]

    # Default for _path set in artifact_path_init() below
    _path: Mapped[pathlib.Path] = mapped_column(
        "path", unique=True, nullable=False, default=_artifact_path_default
    )

    import_id: Mapped[int] = mapped_column(ForeignKey(Import.id))
    import_: Mapped[Import] = relationship(back_populates="artifacts")

    source_uri: Mapped[str | None]
    file_name: Mapped[str]

    tasks: Mapped[set["ArtifactTask"]] = relationship(back_populates="artifact")

    def __new__(cls, *args: tuple[Any], **kwargs: dict[str, Any]) -> "Artifact":
        if not Artifact.artifacts_root:
            Artifact.artifacts_root = pathlib.Path(config["artifacts"]["root"])
        return super().__new__(cls)

    @hybrid_property
    def path(self) -> pathlib.PurePath:
        return pathlib.PurePath(self._path)

    @path.setter
    def path(self, value: pathlib.PurePath | str) -> None:
        if isinstance(value, str):
            value = value.rstrip("/")
        if value != self._path and self.full_path.exists():
            new_full_path = self.artifacts_root / value
            os.makedirs(new_full_path.parent, exist_ok=True)
            new_full_path.hardlink_to(self.full_path)
            self._sessions_added_files[object_session(self)].add(new_full_path)
            self._sessions_removed_files[object_session(self)].add(self.full_path)

        self._path = value

    @path.expression
    def path(cls) -> SQLColumnExpression:
        return cls._path

    @property
    def full_path(self) -> pathlib.Path:
        return self.artifacts_root / self.path

    @property
    def async_full_path(self) -> AsyncPath:
        return AsyncPath(self.full_path)

    @property
    def data(self) -> bytes:
        if self.full_path in self._sessions_removed_files[object_session(self)]:
            raise FileNotFoundError(errno.ENOENT, "No such file or directory")

        with self.full_path.open("rb") as fp:
            return fp.read()

    @data.setter
    def data(self, data: bytes) -> None:
        os.makedirs(self.full_path.parent, exist_ok=True)

        with os.fdopen(os.open(self.full_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY), "wb") as fp:
            fp.write(data)
            self.content_type = mime.buffer(data)

        self._sessions_added_files[object_session(self)].add(self.full_path)

    @data.deleter
    def data(self) -> None:
        self._sessions_removed_files[object_session(self)].add(self.full_path)


@event.listens_for(Session, "after_commit")
def _finalize_files_on_commit(session) -> None:
    for removed_path in Artifact._sessions_removed_files[session]:
        removed_path.unlink()
    del Artifact._sessions_removed_files[session]
    Artifact._sessions_added_files.pop(session, None)


@event.listens_for(Session, "after_soft_rollback")
def _finalize_files_on_rollback(session, previous_transaction) -> None:
    for added_path in Artifact._sessions_added_files[session]:
        added_path.unlink()
    del Artifact._sessions_added_files[session]
    Artifact._sessions_removed_files.pop(session, None)
