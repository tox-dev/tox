from __future__ import annotations

import logging
from itertools import chain
from pathlib import Path
from typing import TYPE_CHECKING

from tox.config.types import MissingRequiredConfigKeyError
from tox.report import HandledError

from .legacy_toml import LegacyToml
from .setup_cfg import SetupCfg
from .toml_pyproject import TomlPyProject
from .toml_tox import TomlTox
from .tox_ini import ToxIni

if TYPE_CHECKING:
    from .api import Source

SOURCE_TYPES: tuple[type[Source], ...] = (
    ToxIni,
    SetupCfg,
    LegacyToml,
    TomlPyProject,
    TomlTox,
)


def discover_source(config_file: Path | None, root_dir: Path | None) -> Source:
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
    elif config_file.is_dir():
        src = None
        for src_type in SOURCE_TYPES:
            candidate: Path = config_file / src_type.FILENAME
            try:
                src = src_type(candidate)
                break
            except ValueError:
                continue
        if src is None:
            msg = f"could not find any config file in {config_file}"
            raise HandledError(msg)
    else:
        src = _load_exact_source(config_file)
    return src


def _locate_source() -> Source | None:
    folder = Path.cwd()
    for base in chain([folder], folder.parents):
        for src_type in SOURCE_TYPES:
            candidate: Path = base / src_type.FILENAME
            if candidate.exists():
                try:
                    return src_type(candidate)
                except MissingRequiredConfigKeyError as exc:
                    msg = f"{src_type.__name__} skipped loading {candidate.resolve()} due to {exc}"
                    logging.info(msg)
                except ValueError as exc:
                    msg = f"{src_type.__name__} failed loading {candidate.resolve()} due to {exc}"
                    raise HandledError(msg) from exc
    return None


def _load_exact_source(config_file: Path) -> Source:
    # if the filename matches to the letter some config file name do not fallback to other source types
    if not config_file.exists():
        msg = f"config file {config_file} does not exist"
        raise HandledError(msg)
    exact_match = [s for s in SOURCE_TYPES if config_file.name == s.FILENAME]  # pragma: no cover
    for src_type in exact_match or SOURCE_TYPES:  # pragma: no branch
        try:
            return src_type(config_file)
        except MissingRequiredConfigKeyError:  # noqa: PERF203
            pass
        except ValueError as exc:
            msg = f"{src_type.__name__} failed loading {config_file.resolve()} due to {exc}"
            raise HandledError(msg) from exc
    msg = f"could not recognize config file {config_file}"
    raise HandledError(msg)


def _create_default_source(root_dir: Path | None) -> Source:
    if root_dir is None:  # if set use that
        empty = Path.cwd()
        for base in chain([empty], empty.parents):
            if (base / "pyproject.toml").exists():
                empty = base
                break
    else:  # if not set use where we find pyproject.toml in the tree or cwd
        empty = root_dir
    names = " or ".join({i.FILENAME: None for i in SOURCE_TYPES})
    logging.warning("No loadable %s found, assuming empty tox.ini at %s", names, empty)
    return ToxIni(empty / "tox.ini", content="")


__all__ = ("discover_source",)
