# SPDX-FileCopyrightText: SQLAlchemy authors and contributors
#
# SPDX-License-Identifier: MIT

import datetime as dt
from typing import Any

from sqlalchemy.engine import Dialect
from sqlalchemy.types import DateTime, TypeDecorator, TypeEngine


class TZDateTime(TypeDecorator[dt.datetime]):
    """Store time zone aware timestamps as time zone naive UTC.

    Taken from
    https://docs.sqlalchemy.org/en/14/core/custom_types.html#store-timezone-aware-timestamps-as-timezone-naive-utc
    """

    impl: TypeEngine[Any] | type[TypeEngine[Any]] = DateTime
    cache_ok: bool | None = True

    def process_bind_param(self, value: dt.datetime | None, dialect: Dialect) -> dt.datetime | None:
        if value is not None:
            if not value.tzinfo:
                raise TypeError("tzinfo is required")
            value = value.astimezone(dt.UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value: dt.datetime | None, dialect: Dialect) -> Any:
        if value is not None:
            value = value.replace(tzinfo=dt.UTC)
        return value
