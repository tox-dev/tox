import sys
from configparser import ConfigParser
from pathlib import Path
from typing import Callable, List, Optional

import pytest

from tox.config.main import Config
from tox.config.source.tox_ini import ToxIni

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
        tox_ini_file = tmp_path / "tox.ini"
        tox_ini_file.write_text(f"[testenv:py]\nenv={conf}\n")
        tox_ini = ToxIni(tox_ini_file)
        config = Config(tox_ini, overrides=[], root=tmp_path, pos_args=pos_args, work_dir=tmp_path)
        loader = config.get_env("py").loaders[0]
        return loader.load(key="env", of_type=str, conf=config, env_name="a", chain=[])

    return example  # noqa
