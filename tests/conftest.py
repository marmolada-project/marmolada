from collections.abc import Iterator
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
import yaml
from click.testing import CliRunner

from marmolada.core.configuration import config, read_configuration

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
                if marker.kwargs.get("clear"):
                    configs = []
                objtype = marker.kwargs.get("objtype", Path)
                assert objtype in (Path, str)
                if marker.kwargs.get("example_config"):
                    configs.append((objtype, EXAMPLE_CONFIG_SENTINEL))
                for content in marker.args:
                    assert any(isinstance(content, t) for t in (dict, str))
                    configs.append((objtype, content))

    # Create configuration files.
    config_file_paths = []  # their Path or str counterparts
    for objtype, content in configs:
        if content is EXAMPLE_CONFIG_SENTINEL:
            config_file_paths.append(EXAMPLE_CONFIG.absolute())
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

    # Let tests work with the configuration files.
    yield config_file_paths


@pytest.fixture(autouse=True)
def marmolada_config(marmolada_config_files, tmp_path, request):
    """Fixture to apply temporary configuration files in tests.

    This loads the configuration files which are specified using
    @pytest.mark.marmolada_config(...) (see marmolada_config_files) and applies
    them in marmolada.core.configuration.config.
    """
    read_configuration(*marmolada_config_files, clear=True)

    # Optionally, override artifacts root path with a temporary, empty one for tests.
    tweak_for_tests = True
    for node in request.node.listchain():
        for marker in node.own_markers:
            if marker.name == "marmolada_config":
                tweak_for_tests = marker.kwargs.get("tweak_for_tests", tweak_for_tests)
    if tweak_for_tests:
        if "artifacts" in config:
            test_artifacts_root = tmp_path / "test_artifacts"
            test_artifacts_root.mkdir()
            config["artifacts"]["root"] = str(test_artifacts_root)


# Misc fixtures


@pytest.fixture
def cli_runner():
    return CliRunner()
