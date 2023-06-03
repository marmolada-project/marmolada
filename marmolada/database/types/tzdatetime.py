# SPDX-FileCopyrightText: SQLAlchemy authors and contributors
#
# SPDX-License-Identifier: MIT

import datetime as dt

from sqlalchemy.types import DateTime, TypeDecorator


class TZDateTime(TypeDecorator):
    """Store time zone aware timestamps as time zone naive UTC.

    Taken from
    https://docs.sqlalchemy.org/en/14/core/custom_types.html#store-timezone-aware-timestamps-as-timezone-naive-utc
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if not value.tzinfo:
                raise TypeError("tzinfo is required")
            value = value.astimezone(dt.UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = value.replace(tzinfo=dt.UTC)
        return value
