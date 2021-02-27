import logging
from itertools import chain
from pathlib import Path
from typing import Optional, Tuple, Type

from tox.report import HandledError

from .api import Source
from .legacy_toml import LegacyToml
from .setup_cfg import SetupCfg
from .tox_ini import ToxIni

SOURCE_TYPES: Tuple[Type[Source], ...] = (ToxIni, SetupCfg, LegacyToml)


def discover_source(config_file: Optional[Path], root_dir: Optional[Path]) -> Source:
    """
    Discover a source for configuration.

    :param config_file: the file storing the source
    :param root_dir: the root directory as set by the user (None means not set)
    :return: the source of the config
    """
    if config_file is None:
        src = _locate_source()
        if src is None:
            src = _create_default_source(root_dir)
    else:
        src = _load_exact_source(config_file)
    return src


def _locate_source() -> Optional[Source]:
    folder = Path.cwd()
    for base in chain([folder], folder.parents):
        for src_type in SOURCE_TYPES:
            candidate: Path = base / src_type.FILENAME
            try:
                return src_type(candidate)
            except ValueError:
                pass
    return None


def _load_exact_source(config_file: Path) -> Source:
    for src_type in SOURCE_TYPES:  # pragma: no branch # SOURCE_TYPES will never be empty
        if src_type.FILENAME == config_file.name:
            try:
                return src_type(config_file)
            except ValueError:
                pass
    raise HandledError(f"could not recognize config file {config_file}")


def _create_default_source(root_dir: Optional[Path]) -> Source:
    if root_dir is None:  # if set use that
        empty = Path.cwd()
        for base in chain([empty], empty.parents):
            if (base / "pyproject.toml").exists():
                empty = base
                break
    else:  # if not set use where we find pyproject.toml in the tree or cwd
        empty = root_dir
    logging.warning(f"No {' or '.join(i.FILENAME for i in SOURCE_TYPES)} found, assuming empty tox.ini at {empty}")
    src = ToxIni(empty / "tox.ini", content="")
    return src


__all__ = ("discover_source",)
