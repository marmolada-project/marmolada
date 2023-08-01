# SPDX-FileCopyrightText: Copyright Mike Bayer
# SPDX-FileCopyrightText: Copyright Nils Philippsen
#
# SPDX-License-Identifier: MIT

import enum
from functools import cache

from sqlalchemy.types import Enum, SchemaType, TypeDecorator

from ...core.util import camel_case_to_lower_with_underscores

# adapted from http://techspot.zzzeek.org/2011/01/14/the-enum-recipe
# changes:
# - support Python 3.x only
# - derive from enum.Enum to be usable in pydantic models, therefore doesn't use EnumSymbol
# - don’t use a custom metaclass
# - improve auto-generated db-side type name


class DeclEnum(enum.Enum):
    """A declarative enumeration type for SQLAlchemy models."""

    @classmethod
    @cache
    def db_type(cls):
        return DeclEnumType(cls)

    @classmethod
    def from_string(cls, value):
        try:
            return cls.__members__[value]
        except KeyError as exc:
            raise ValueError(f"Invalid value for {cls.__name__!r}: {value!r}") from exc

    @classmethod
    def values(cls):
        return cls.__members__.keys()


class DeclEnumType(SchemaType, TypeDecorator):
    """A persistable column type tied to a DeclEnum type."""

    cache_ok = True

    def __init__(self, enum):
        self.enum = enum
        self.impl = Enum(*enum.values(), name=self._type_name(enum.__name__))

    @classmethod
    def _type_name(cls, clsname):
        return camel_case_to_lower_with_underscores(clsname) + "_enum"

    def _set_table(self, table, column):
        self.impl._set_table(table, column)

    def copy(self):
        return DeclEnumType(self.enum)

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, str):
            value = self.process_result_value(value, dialect)
        return value.value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum.from_string(value.strip())
