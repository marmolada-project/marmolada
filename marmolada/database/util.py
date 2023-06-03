from sqlalchemy import Column, DateTime
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement

from .types.tzdatetime import TZDateTime


class utcnow(FunctionElement):
    """Current timestamp in UTC for SQL expressions."""

    type = DateTime
    inherit_cache = True


@compiles(utcnow, "postgresql")
def _postgresql_utcnow(element, compiler, **kwargs):
    return "(NOW() AT TIME ZONE 'utc')"


class Creatable:
    created_at = Column(TZDateTime, nullable=False, default=utcnow())


class Updatable:
    updated_at = Column(TZDateTime, nullable=False, default=utcnow(), onupdate=utcnow())
