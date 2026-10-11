import pathlib
from typing import Any

from sqlalchemy import UnicodeText
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine


class Path(TypeDecorator[str]):
    cache_ok: bool | None = True
    impl: TypeEngine[Any] | type[TypeEngine[Any]] = UnicodeText

    def process_bind_param(
        self, value: pathlib.PurePath | str | None, dialect: Dialect
    ) -> str | None:
        if value is None:
            return None
        elif isinstance(value, str):
            value = value.rstrip("/")
        else:
            value = str(value)
        return value

    def process_result_value(self, value: str | None, dialect: Dialect) -> Any:
        if value is None:
            return None
        return pathlib.PurePath(value)
