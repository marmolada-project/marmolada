import datetime as dt
from typing import Any
from uuid import UUID, uuid1

from sqlalchemy import Uuid
from sqlalchemy.event import listens_for
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, QueryableAttribute, mapped_column

from .types.tzdatetime import TZDateTime
from .util import utcnow

__all__ = ("Creatable", "Updatable", "UuidPrimaryKey")


class Creatable:
    created_at: Mapped[dt.datetime] = mapped_column(TZDateTime, nullable=False, default=utcnow())


class Updatable:
    updated_at: Mapped[dt.datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow(), onupdate=utcnow()
    )


class UuidPrimaryKey:
    _uuid: Mapped[UUID] = mapped_column("uuid", Uuid, primary_key=True, default=uuid1)

    @hybrid_property
    def uuid(self) -> UUID:
        return self._uuid

    @uuid.setter
    def uuid(self, value: UUID) -> None:
        if self._uuid:
            raise AttributeError(f"Can’t modify {type(self).__name__}.uuid")
        self._uuid = value

    @uuid.expression
    def uuid(cls) -> QueryableAttribute:
        return cls._uuid


@listens_for(UuidPrimaryKey, "init", propagate=True)
def uuid_primary_key_init(target: UuidPrimaryKey, args: tuple[Any], kwargs: dict[str, Any]) -> None:
    # Ensure uuid is available early
    kwargs["uuid"] = kwargs.get("uuid") or uuid1()
