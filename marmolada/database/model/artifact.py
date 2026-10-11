import errno
import logging
import os
import pathlib
from collections import defaultdict
from typing import TYPE_CHECKING, ClassVar

from anyio import Path as AsyncPath
from sqlalchemy import ForeignKey, event
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import (
    Mapped,
    QueryableAttribute,
    Session,
    mapped_column,
    object_session,
    relationship,
)
from sqlalchemy.orm.collections import attribute_keyed_dict
from sqlalchemy.sql import SQLColumnExpression

from ...core.configuration import config
from ...core.types import JSONDict
from .. import Base
from ..mixins import BigIntPrimaryKey, Creatable, Updatable, UuidAltKey
from .metadata import ArtifactMetadata

if TYPE_CHECKING:
    from .metadata import JSONValue
    from .task import ArtifactTask, ImportTask

log = logging.getLogger(__name__)


class Import(Base, BigIntPrimaryKey, UuidAltKey, Creatable, Updatable):
    __tablename__ = "imports"

    meta: Mapped[JSONDict] = mapped_column(default=dict)
    _complete: Mapped[bool] = mapped_column("complete", default=False)
    artifacts: Mapped[set[Artifact]] = relationship(back_populates="import_")

    tasks: Mapped[set[ImportTask]] = relationship(back_populates="import_")

    @hybrid_property
    def complete(self) -> bool:
        return self._complete

    @complete.inplace.setter
    def _complete_setter(self, value: bool) -> None:
        if self._complete and not value:
            raise ValueError("Completed import can’t be set incomplete.")
        self._complete = value

    @complete.inplace.expression
    @classmethod
    def _complete_expression(cls) -> QueryableAttribute:
        return cls._complete


def _artifact_path_default(context: DefaultExecutionContext) -> str:
    params = context.get_current_parameters()
    uuid = params["uuid"]
    import_id = params["import_id"]
    file_name = params["file_name"]
    return f"incoming/import-{import_id}-artifact-{uuid}-{file_name}"


class Artifact(Base, BigIntPrimaryKey, UuidAltKey, Creatable, Updatable):
    __tablename__ = "artifacts"

    artifacts_root: ClassVar[pathlib.Path]

    _sessions_added_files: ClassVar = defaultdict(set)
    _sessions_removed_files: ClassVar = defaultdict(set)

    content_type: Mapped[str | None]

    _path: Mapped[pathlib.PurePath] = mapped_column(
        "path", unique=True, nullable=False, default=_artifact_path_default
    )

    import_id: Mapped[int] = mapped_column(ForeignKey(Import.id), index=True)
    import_: Mapped[Import] = relationship(back_populates="artifacts")

    source_uri: Mapped[str | None]
    file_name: Mapped[str]

    metadata_objs: Mapped[dict[str, ArtifactMetadata]] = relationship(
        back_populates="artifact",
        collection_class=attribute_keyed_dict("name"),
        cascade="all, delete-orphan",
    )
    metadata_: AssociationProxy[dict[str, JSONValue]] = association_proxy(
        "metadata_objs", "value", creator=lambda k, v: ArtifactMetadata(name=k, value=v)
    )

    tasks: Mapped[set[ArtifactTask]] = relationship(back_populates="artifact")

    def __new__(cls, *args: object, **kwargs: object) -> Artifact:
        if not getattr(Artifact, "artifacts_root", None):
            Artifact.artifacts_root = pathlib.Path(config["artifacts"]["root"])
        return super().__new__(cls)

    @hybrid_property
    def path(self) -> pathlib.PurePath:
        return pathlib.PurePath(self._path)

    @path.inplace.setter
    def _path_setter(self, value: pathlib.PurePath | str) -> None:
        if isinstance(value, str):
            value = pathlib.PurePath(value.rstrip("/"))

        if value != self._path and self.full_path.exists():
            new_full_path = self.artifacts_root / value
            os.makedirs(new_full_path.parent, exist_ok=True)
            new_full_path.hardlink_to(self.full_path)
            self._sessions_added_files[object_session(self)].add(new_full_path)
            self._sessions_removed_files[object_session(self)].add(self.full_path)

        self._path = value

    @path.inplace.expression
    @classmethod
    def _path_expression(cls) -> SQLColumnExpression:
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
