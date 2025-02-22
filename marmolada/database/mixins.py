import datetime as dt
from typing import Any
from uuid import UUID, uuid1

from sqlalchemy import BigInteger, Identity, Uuid, text
from sqlalchemy.event import listens_for
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, QueryableAttribute, mapped_column

from .types.tzdatetime import TZDateTime
from .util import utcnow

__all__ = ("BigIntPrimaryKey", "Creatable", "Updatable", "UuidAltKey")


class BigIntPrimaryKey:
    id: Mapped[BigInteger] = mapped_column(
        "id", BigInteger, Identity(), primary_key=True, sort_order=-30
    )


class UuidAltKey:
    _uuid: Mapped[UUID] = mapped_column(
        "uuid",
        Uuid,
        unique=True,
        default=uuid1,
        server_default=text("gen_random_uuid()"),
        nullable=False,
        sort_order=-20,
    )

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


@listens_for(UuidAltKey, "init", propagate=True)
def uuid_primary_key_init(target: UuidAltKey, args: tuple[Any], kwargs: dict[str, Any]) -> None:
    # Ensure uuid is available early
    kwargs["uuid"] = kwargs.get("uuid") or uuid1()


class Creatable:
    created_at: Mapped[dt.datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow(), sort_order=-10
    )


class Updatable:
    updated_at: Mapped[dt.datetime] = mapped_column(
        TZDateTime, nullable=False, default=utcnow(), onupdate=utcnow(), sort_order=-9
    )
