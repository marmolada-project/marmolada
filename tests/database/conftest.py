import psycopg
import pytest
import pytest_postgresql
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import create_async_engine

from marmolada.database.main import Base, _async_from_sync_url, init_model, session_maker

# Like postgresql_proc, but scoped for test functions. This makes testing slower but ensures that
# tests don't affect each other, especially if conducted in parallel.
postgresql_function_proc = pytest.fixture(scope="function")(
    pytest_postgresql.factories.postgresql_proc().__wrapped__
)


@pytest.fixture
def postgresql_sync_url(postgresql_function_proc) -> URL:
    url = URL.create(
        drivername="postgresql",
        username="postgres",
        host=postgresql_function_proc.host,
        port=postgresql_function_proc.port,
        database="marmolada",
    )
    return url


@pytest.fixture
def postgresql_async_url(postgresql_sync_url) -> URL:
    return _async_from_sync_url(postgresql_sync_url)


@pytest.fixture
def postgresql_db(postgresql_sync_url, postgresql_async_url) -> tuple[URL, URL]:
    admin_url = postgresql_sync_url.set(database="postgres")

    with psycopg.connect(str(admin_url), autocommit=True) as conn, conn.cursor() as cur:
        cur.execute('CREATE DATABASE "marmolada"')
        conn.commit()

    return postgresql_sync_url, postgresql_async_url


@pytest.fixture
def db_engine(postgresql_async_url, postgresql_db):
    """A fixture which creates an asynchronous database engine."""
    db_engine = create_async_engine(
        url=postgresql_async_url,
        future=True,
        echo=True,
        isolation_level="SERIALIZABLE",
    )
    return db_engine


@pytest.fixture
async def db_schema(db_engine):
    """Asynchronous fixture to install the database schema."""
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def db_model_initialized(db_engine, db_schema):
    """Fixture to initialize the asynchronous DB model.

    This is used so db_session is usable in tests.
    """
    init_model(engine=db_engine)


@pytest.fixture
async def db_session(db_model_initialized):
    """Fixture setting up an asynchronous DB session."""
    db_session = session_maker()
    try:
        yield db_session
    finally:
        await db_session.close()
