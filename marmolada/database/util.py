from sqlalchemy import DateTime
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement


class utcnow(FunctionElement):
    """Current timestamp in UTC for SQL expressions."""

    type = DateTime
    inherit_cache = True


@compiles(utcnow, "postgresql")
def _postgresql_utcnow(element, compiler, **kwargs):
    return "(NOW() AT TIME ZONE 'utc')"
