import pathlib
from copy import deepcopy
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy import types as sqla_types
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..core.configuration import config
from . import types

# use custom metadata to specify naming convention
naming_convention = {
    "ix": "%(table_name)s_%(column_0_N_label)s_index",
    "uq": "%(table_name)s_%(column_0_N_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}
metadata = MetaData(naming_convention=naming_convention)

type_annotation_map = {
    str: sqla_types.UnicodeText(),
    pathlib.Path: types.Path(),
    dict[str, Any]: JSONB(),
}


class Base(DeclarativeBase, AsyncAttrs):
    metadata = metadata
    type_annotation_map = type_annotation_map


session_maker: AsyncSession = sessionmaker(class_=AsyncSession, expire_on_commit=False, future=True)


def init_model(engine: AsyncEngine = None) -> None:
    if not engine:
        engine = get_engine()
    session_maker.configure(bind=engine)


def _async_from_sync_url(url: URL | str) -> URL:
    """Create an async DB URL from a conventional one."""
    sync_url = make_url(url)

    try:
        dialect, _ = sync_url.drivername.split("+", 1)
    except ValueError:
        dialect = sync_url.drivername

    match dialect:
        case "sqlite":
            driver = "aiosqlite"
        case "postgresql":
            driver = "asyncpg"
        case _:
            raise ValueError(f"Don't know asyncio driver for dialect {dialect}")

    return sync_url.set(drivername=f"{dialect}+{driver}")


def get_engine() -> AsyncEngine:
    sqla_config = deepcopy(config["database"]["sqlalchemy"])
    sqla_config["url"] = _async_from_sync_url(sqla_config["url"])
    return create_async_engine(**sqla_config)
