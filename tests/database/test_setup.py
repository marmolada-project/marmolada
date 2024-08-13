from contextlib import nullcontext
from unittest import mock

import pytest

from marmolada.database import setup


@pytest.mark.parametrize(
    "db_empty, existing_ok",
    (
        (True, False),
        (False, False),
        (False, True),
    ),
    ids=("db-empty", "db-not-empty-existing-fatal", "db-not-empty-existing-ok"),
)
@mock.patch.dict("marmolada.database.setup.config")
@mock.patch("marmolada.database.setup.alembic")
@mock.patch("marmolada.database.setup.metadata")
@mock.patch("marmolada.database.setup.inspect")
@mock.patch("marmolada.database.setup.create_engine")
def test_setup_db_schema(create_engine, inspect, metadata, alembic, db_empty, existing_ok, capsys):
    create_engine.return_value = engine = mock.MagicMock()
    inspection_result = inspect.return_value
    inspection_result.get_table_names.return_value = [] if db_empty else ["boo"]
    alembic_cfg = alembic.config.Config.return_value
    setup.config["database"] = {"sqlalchemy": {"url": "boo"}}

    if db_empty:
        expectation = nullcontext()
    else:
        expectation = pytest.raises(SystemExit)

    with expectation as excinfo:
        setup.setup_db_schema(existing_ok=existing_ok)

    if db_empty:
        metadata.create_all.assert_called_with(bind=engine)
        assert alembic_cfg.set_main_option.call_count > 0
        alembic.command.stamp.assert_called_once_with(alembic_cfg, "head")
    else:
        assert excinfo.value.code == 0 if existing_ok else 1

        stdout, stderr = capsys.readouterr()
        output = stdout if existing_ok else stderr

        assert "Tables already present: boo\n" in output
        assert "Refusing to change database schema." in output

        metadata.create_all.assert_not_called()
        alembic_cfg.set_main_option.assert_not_called()
        alembic.command.stamp.assert_not_called()
