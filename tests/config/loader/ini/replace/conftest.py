from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.config.cli.parser import Parsed
from tox.config.loader.api import ConfigLoadArgs
from tox.config.main import Config
from tox.config.source.tox_ini import ToxIni

if TYPE_CHECKING:
    from pathlib import Path

from typing import Protocol


class ReplaceOne(Protocol):
    def __call__(self, conf: str, pos_args: list[str] | None = None) -> str: ...


@pytest.fixture
def replace_one(tmp_path: Path) -> ReplaceOne:
    def example(conf: str, pos_args: list[str] | None = None) -> str:
        tox_ini_file = tmp_path / "tox.ini"
        tox_ini_file.write_text(f"[testenv:py]\nenv={conf}\n")
        tox_ini = ToxIni(tox_ini_file)

        config = Config(
            tox_ini,
            options=Parsed(override=[]),
            root=tmp_path,
            pos_args=pos_args,
            work_dir=tmp_path,
        )
        loader = config.get_env("py").loaders[0]
        args = ConfigLoadArgs(chain=[], name="a", env_name="a")
        return loader.load(key="env", of_type=str, conf=config, factory=None, args=args)

    return example
