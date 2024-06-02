from uuid import UUID

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .. import Base
from ..mixins import Creatable, UuidPrimaryKey
from .artifact import Artifact, Import


class TaskMixin(Creatable, UuidPrimaryKey):
    name: Mapped[str]


class ArtifactTask(Base, TaskMixin):
    __tablename__ = "artifact_tasks"
    __table_args__ = (UniqueConstraint("name", "artifact_uuid"),)

    artifact_uuid: Mapped[UUID] = mapped_column(ForeignKey(Artifact.uuid))
    artifact: Mapped[Artifact] = relationship(back_populates="tasks")


class ImportTask(Base, TaskMixin):
    __tablename__ = "import_tasks"
    __table_args__ = (UniqueConstraint("name", "import_uuid"),)

    import_uuid: Mapped[UUID] = mapped_column(ForeignKey(Import.uuid))
    import_: Mapped[Import] = relationship(back_populates="tasks")
