import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Callable, List, Optional

import pytest

from tox.config.loader.ini import IniLoader
from tox.config.main import Config

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from typing import Protocol
else:  # pragma: no cover (<py38)
    from typing_extensions import Protocol  # noqa


class ReplaceOne(Protocol):
    def __call__(self, conf: str, pos_args: Optional[List[str]] = None) -> str:
        ...


@pytest.fixture
def replace_one(mk_ini_conf: Callable[[str], ConfigParser], tmp_path: Path) -> ReplaceOne:
    def example(conf: str, pos_args: Optional[List[str]] = None) -> str:
        parser = mk_ini_conf(f"[testenv]\nenv={conf}\n")
        loader = IniLoader("testenv", parser, [])
        config = Config(None, overrides=[], root=tmp_path, pos_args=pos_args, work_dir=tmp_path)  # type: ignore
        return loader.load(key="env", of_type=str, conf=config, env_name="a")

    return example  # noqa
