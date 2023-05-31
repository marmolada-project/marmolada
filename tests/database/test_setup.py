from contextlib import nullcontext
from unittest import mock

import pytest

from marmolada.database import setup


@pytest.mark.parametrize("db_empty", (True, False), ids=("db-empty", "db-not-empty"))
@mock.patch.dict("marmolada.database.setup.config")
@mock.patch("marmolada.database.setup.alembic")
@mock.patch("marmolada.database.setup.metadata")
@mock.patch("marmolada.database.setup.inspect")
@mock.patch("marmolada.database.setup.get_engine")
async def test_setup_db_schema(get_engine, inspect, metadata, alembic, db_empty, capsys):
    get_engine.return_value = engine = mock.MagicMock()
    inspection_result = inspect.return_value
    inspection_result.has_table.return_value = not db_empty
    metadata.tables = ["boo"]
    alembic_cfg = alembic.config.Config.return_value
    setup.config["database"] = {"sqlalchemy": {"url": "boo"}}

    if db_empty:
        expectation = nullcontext()
    else:
        expectation = pytest.raises(SystemExit)

    with expectation:
        await setup.setup_db_schema()

    if db_empty:
        metadata.create_all.assert_called_with(bind=engine)
        assert alembic_cfg.set_main_option.call_count > 0
        alembic.command.stamp.assert_called_once_with(alembic_cfg, "head")
    else:
        stdout, stderr = capsys.readouterr()
        assert "Tables already present: boo\n" in stderr
        assert "Refusing to change database schema." in stderr

        metadata.create_all.assert_not_called()
        alembic_cfg.set_main_option.assert_not_called()
        alembic.command.stamp.assert_not_called()


def test__gen_test_data_objs():
    result = setup._gen_test_data_objs()
    assert isinstance(result, set)
