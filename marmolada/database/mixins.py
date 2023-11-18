from sqlalchemy import Column
from sqlalchemy.orm import declared_attr

from .types.tzdatetime import TZDateTime
from .util import utcnow

__all__ = ("Creatable", "Updatable")


class Creatable:
    @declared_attr
    def created_at(cls):
        return Column(TZDateTime, nullable=False, default=utcnow())


class Updatable:
    @declared_attr
    def updated_at(cls):
        return Column(TZDateTime, nullable=False, default=utcnow(), onupdate=utcnow())
