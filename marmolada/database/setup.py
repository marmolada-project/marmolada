import sys
from pathlib import Path

import alembic.command
import alembic.config
from sqlalchemy import create_engine, inspect

from ..core.configuration import config

# Import the DB model here so its classes are considered by metadata.create_all() below.
from . import model  # noqa: F401
from .main import metadata

HERE = Path(__file__).parent


def setup_db_schema(existing_ok: bool = False) -> None:
    engine = create_engine(**config["database"]["sqlalchemy"])

    inspection_result = inspect(engine)

    present_tables = sorted(inspection_result.get_table_names())

    if present_tables:
        print(
            f"Tables already present: {', '.join(present_tables)}\n"
            + "Refusing to change database schema.",
            file=sys.stdout if existing_ok else sys.stderr,
        )
        sys.exit(0 if existing_ok else 1)

    with engine.begin():
        print("Creating database schema")
        metadata.create_all(bind=engine)

        print("Setting up database migrations")
        cfg = alembic.config.Config()
        cfg.set_main_option("script_location", str(HERE / "migrations"))
        cfg.set_main_option("sqlalchemy.url", config["database"]["sqlalchemy"]["url"])

        alembic.command.stamp(cfg, "head")
