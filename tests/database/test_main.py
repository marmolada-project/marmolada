from contextlib import nullcontext
from unittest import mock

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from marmolada.database import main


@pytest.mark.parametrize("with_engine", (True, False))
@mock.patch("marmolada.database.main.session_maker")
@mock.patch("marmolada.database.main.get_engine")
def test_init_model(get_engine, session_maker, with_engine):
    if with_engine:
        engine = object()
        main.init_model(engine=engine)
    else:
        get_engine.return_value = engine = object()
        main.init_model()

    if with_engine:
        get_engine.assert_not_called()
    else:
        get_engine.assert_called_once_with()

    session_maker.configure.assert_called_with(bind=engine)


@pytest.mark.parametrize(
    "testcase", ("with-postgresql", "with-sqlite", "with-postgresql-driver", "with-unknown")
)
def test__async_from_sync_url(testcase):
    expectation = nullcontext()

    if "with-postgresql" in testcase:
        sync_url = "postgresql"
        expected = "postgresql+asyncpg:///"
    elif "with-sqlite" in testcase:
        sync_url = "sqlite"
        expected = "sqlite+aiosqlite:///"
    elif "with-unknown" in testcase:
        sync_url = "unknown"
        expectation = pytest.raises(ValueError)

    if "driver" in testcase:
        sync_url += "+driver"

    sync_url += ":///"

    with expectation:
        async_url = main._async_from_sync_url(sync_url)

    if "with-unknown" not in testcase:
        assert str(async_url) == expected


@mock.patch.dict("marmolada.database.main.config")
def test_get_engine():
    sync_url = "postgresql:///"
    main.config["database"] = {"sqlalchemy": {"url": sync_url}}

    engine = main.get_engine()

    assert isinstance(engine, AsyncEngine)
    assert engine.url == main._async_from_sync_url(sync_url)
