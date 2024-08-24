from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .. import Base
from ..mixins import BigIntPrimaryKey, Creatable, UuidAltKey
from .artifact import Artifact, Import


class TaskMixin(BigIntPrimaryKey, UuidAltKey, Creatable):
    name: Mapped[str]


class ArtifactTask(Base, TaskMixin):
    __tablename__ = "artifact_tasks"
    __table_args__ = (UniqueConstraint("name", "artifact_id"),)

    artifact_id: Mapped[int] = mapped_column(ForeignKey(Artifact.id))
    artifact: Mapped[Artifact] = relationship(back_populates="tasks")


class ImportTask(Base, TaskMixin):
    __tablename__ = "import_tasks"
    __table_args__ = (UniqueConstraint("name", "import_id"),)

    import_id: Mapped[int] = mapped_column(ForeignKey(Import.id))
    import_: Mapped[Import] = relationship(back_populates="tasks")
