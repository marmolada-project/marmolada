from pathlib import Path

import toml

from marmolada import version

HERE = Path(__file__).parent
PYPROJECT_TOML_PATH = HERE.parent / "pyproject.toml"


class TestVersion:
    def test___version__(self):
        pyproject = toml.load(PYPROJECT_TOML_PATH)

        assert version.__version__ == pyproject["tool"]["poetry"]["version"]
