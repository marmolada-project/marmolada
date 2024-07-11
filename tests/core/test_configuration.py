import copy
from pathlib import Path

import pytest
import yaml

from marmolada.core.configuration import main
from marmolada.core.util import merge_dicts

EXAMPLE_CONFIG = {"api": {"host": "127.0.0.1", "port": 8080}}


@pytest.mark.marmolada_config(EXAMPLE_CONFIG, clear=True)
class TestConfiguration:
    @pytest.mark.parametrize("objtype", (str, Path))
    def test__expand_normalize_config_files(self, objtype, tmp_path, marmolada_config_files):
        sub_file1 = tmp_path / "sub_file1.yaml"
        sub_file1.touch()

        sub_file2 = tmp_path / "sub_file2.yaml"
        sub_file2.touch()

        config_files = [*marmolada_config_files, tmp_path]
        expanded_config_files = main._expand_normalize_config_files(
            [objtype(f) for f in config_files]
        )

        assert expanded_config_files == [*marmolada_config_files, sub_file1, sub_file2]

    @pytest.mark.marmolada_config(tweak_for_tests=False)
    @pytest.mark.parametrize("clear", (True, False))
    def test_read_configuration_clear(self, clear, marmolada_config_files):
        main.read_configuration(clear=clear)
        if clear:
            assert all(value is None for value in main.config.values())
        else:
            assert main.config == EXAMPLE_CONFIG

    @pytest.mark.marmolada_config({}, objtype=str, clear=False)
    def test_read_configuration_str(self, marmolada_config_files):
        assert main.config == EXAMPLE_CONFIG

    @pytest.mark.marmolada_config({"api": {"loglevel": "debug"}})
    def test_read_configuration_multiple(self, marmolada_config_files):
        assert len(marmolada_config_files) > 1
        expected_config = copy.deepcopy(EXAMPLE_CONFIG)
        expected_config["api"]["loglevel"] = "debug"
        assert main.config == expected_config

    @pytest.mark.marmolada_config({"api": {"host": "host.example.net"}})
    def test_read_configuration_multiple_override(self, marmolada_config_files):
        assert len(marmolada_config_files) > 1
        assert main.config == merge_dicts(EXAMPLE_CONFIG, {"api": {"host": "host.example.net"}})

    @pytest.mark.marmolada_config({"api": {}})
    def test_read_configuration_partial(self, marmolada_config_files, tmp_path):
        assert main.config == EXAMPLE_CONFIG

    @pytest.mark.marmolada_config(example_config=True, clear=True)
    def test_read_configuration_partial_validate_post(self, marmolada_config_files, tmp_path):
        partial_config_file = tmp_path / "partial-config.yaml"
        with partial_config_file.open("w") as fp:
            yaml.dump({"metaclient": {}}, fp)

        main.read_configuration(partial_config_file, clear=True, validate=False)
        main.read_configuration(*marmolada_config_files, clear=False, validate=False)
        main.read_configuration(clear=False, validate=True)

    @pytest.mark.marmolada_config("API__HOST=BOO", objtype="env", clear=True)
    def test_read_configuration_from_env(self, marmolada_config_files):
        assert main.config["api"]["host"] == "BOO"
