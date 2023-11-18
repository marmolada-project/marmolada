import pathlib

from sqlalchemy import UnicodeText
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator


class Path(TypeDecorator):
    cache_ok = True
    impl = UnicodeText

    def process_bind_param(self, value: pathlib.PurePath | str, dialect: Dialect) -> str:
        if value is None:
            return None
        elif isinstance(value, str):
            value = value.rstrip("/")
        else:
            value = str(value)
        return value

    def process_result_value(self, value: str, dialect: Dialect) -> pathlib.PurePath:
        if value is None:
            return None
        return pathlib.PurePath(value)
