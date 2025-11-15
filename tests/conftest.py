import os
from collections.abc import Iterator
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import mock

import psycopg
import pytest
import pytest_postgresql
import yaml
from click.testing import CliRunner
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from marmolada.core.configuration import config, read_configuration
from marmolada.database.main import Base, _async_from_sync_url, init_model, session_maker
from marmolada.database.model import Artifact, Import, Tag, TagLabel

HERE = Path(__file__).parent
EXAMPLE_CONFIG = HERE.parent / "etc" / "marmolada" / "config-example.yaml"

# Configuration fixtures


def pytest_configure(config):
    config.addinivalue_line("markers", "marmolada_config")


@pytest.fixture
def marmolada_config_files(
    request: pytest.FixtureRequest, tmp_path: Path
) -> Iterator[list[Path | str]]:
    """Fixture to create testing configuration files.

    This is useful mainly to the marmolada_config fixture which is applied
    universally, unless you need access to the actual configuration
    files.

    Use `@pytest.mark.marmolada_config()` to affect their content(s), e.g.:

        TEST_CONFIG = {...}

        @pytest.mark.marmolada_config(TEST_CONFIG)
        def test_something(marmolada_config_files):
            # marmolada_config_files is a list containing 1 Path object
            # pointing to the temporary configuration file initialized
            # from TEST_CONFIG
            ...
    """
    configs = []

    EXAMPLE_CONFIG_SENTINEL = object()

    # Consult markers about desired configuration files and their contents.

    # request.node.iter_markers() lists markers of parent objects later, we need them early to make
    # e.g. markers on the method override those on the class.
    for node in request.node.listchain():
        for marker in node.own_markers:
            if marker.name == "marmolada_config":
                objtype = marker.kwargs.get("objtype", Path)
                assert objtype in (Path, str, "env")

                if marker.kwargs.get("clear"):
                    configs = [(objtype, {})]

                if marker.kwargs.get("example_config"):
                    configs.append((objtype, EXAMPLE_CONFIG_SENTINEL))

                for content in marker.args:
                    assert isinstance(content, (dict, str))
                    if objtype == "env" and isinstance(content, str):
                        assert "=" in content
                    configs.append((objtype, content))

    # Create configuration files and environment.
    config_file_paths = []  # their Path or str counterparts
    with mock.patch.dict(os.environ):
        for objtype, content in configs:
            if content is EXAMPLE_CONFIG_SENTINEL:
                config_file_paths.append(EXAMPLE_CONFIG.absolute())
                continue

            if objtype == "env":
                if isinstance(content, str):
                    key, value = content.split("=", 1)
                    if not key.startswith("MARMOLADA_"):
                        key = f"MARMOLADA_{key}"
                    os.environ[key] = value

                continue

            config_file_obj = NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".yaml",
                prefix="tmp_marmolada_test_config",
                delete=False,
            )
            if isinstance(content, dict):
                yaml.dump(content, stream=config_file_obj)
            else:
                print(content, file=config_file_obj)
            config_file_obj.close()
            config_file_paths.append(objtype(config_file_obj.name))

        if not config_file_paths:
            config_file_paths = [EXAMPLE_CONFIG.absolute()]

        # Let tests work with the configuration files.
        yield config_file_paths


@pytest.fixture(autouse=True)
def marmolada_config(marmolada_config_files, tmp_path, request):
    """Fixture to apply temporary configuration files in tests.

    This loads the configuration files which are specified using
    @pytest.mark.marmolada_config(...) (see marmolada_config_files) and applies
    them in marmolada.core.configuration.config.
    """
    read_configuration(*marmolada_config_files)

    # Optionally, override artifacts root path with a temporary, empty one for tests.
    tweak_for_tests = True
    for node in request.node.listchain():
        for marker in node.own_markers:
            if marker.name == "marmolada_config":
                tweak_for_tests = marker.kwargs.get("tweak_for_tests", tweak_for_tests)
    if tweak_for_tests:
        if isinstance(config.get("artifacts"), dict):
            test_artifacts_root = tmp_path / "test_artifacts"
            test_artifacts_root.mkdir()
            config["artifacts"]["root"] = str(test_artifacts_root)


# Misc fixtures


@pytest.fixture
def cli_runner():
    return CliRunner()


# Database fixtures

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
async def db_session(db_model_initialized) -> Iterator[AsyncSession]:
    """Fixture setting up an asynchronous DB session."""
    db_session = session_maker()
    try:
        yield db_session
    finally:
        await db_session.close()


@pytest.fixture
async def db_obj(request, db_session: AsyncSession):
    """Fixture to create an object of a tested model type.

    This is for asynchronous test functions/methods."""
    async with db_session.begin():
        db_obj_dependencies = request.instance._db_obj_get_dependencies()
        attrs = {**request.instance.attrs, **db_obj_dependencies}
        obj = request.instance.cls(**attrs)
        obj._db_obj_dependencies = db_obj_dependencies
        db_session.add(obj)
        await db_session.flush()

        yield obj

        await db_session.rollback()


@pytest.fixture
async def db_test_data_objs() -> dict[str, list[Base]]:
    import_ = Import(complete=True)
    artifact = Artifact(import_=import_, file_name="foo.jpg")
    tags = [
        Tag(label_objs={TagLabel(label="tag0")}),
        Tag(label_objs={TagLabel(label="tag1")}),
        Tag(label_objs={TagLabel(label="tag2")}),
    ]

    return {"imports": [import_], "artifacts": [artifact], "tags": tags}


@pytest.fixture
async def db_test_data(db_session: AsyncSession, db_test_data_objs: list[Base]) -> None:
    """A fixture to fill the DB with test data.

    Use this in asynchronous tests.
    """
    async with db_session.begin():
        db_session.add_all(obj for collection in db_test_data_objs.values() for obj in collection)
