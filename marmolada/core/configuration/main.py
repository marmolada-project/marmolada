from itertools import chain
from pathlib import Path

import yaml

from ..util import merge_dicts
from .validation import ConfigModel

config = {}


def _expand_normalize_config_files(config_files: list[Path | str]) -> list[Path]:
    config_file_paths = []

    for path in config_files:
        if not isinstance(path, Path):
            path = Path(path)
        if path.is_dir():
            config_file_paths.extend(sorted(chain(path.glob("*.yaml"), path.glob("*.yml"))))
        else:
            config_file_paths.append(path)

    return config_file_paths


def read_configuration(*config_files: list[Path | str]):
    config_files = _expand_normalize_config_files(config_files)
    new_config = {}
    for config_file in config_files:
        with config_file.open("r") as fp:
            for config_doc in yaml.safe_load_all(fp):
                new_config = merge_dicts(new_config, config_doc)

    new_config = ConfigModel.model_validate(new_config).model_dump(
        exclude_unset=True, exclude_defaults=True, mode="json"
    )

    config.clear()
    config.update(new_config)
