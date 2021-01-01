import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

import pytest
from _pytest.monkeypatch import MonkeyPatch

from tox.config.cli.parser import Parsed
from tox.config.loader.api import Override
from tox.config.main import Config
from tox.run import make_config

pytest_plugins = "tox.pytest"
HERE = Path(__file__).absolute().parent


@pytest.fixture(scope="session")
def value_error() -> Callable[[str], str]:
    def _fmt(msg: str) -> str:
        return f'ValueError("{msg}"{"," if sys.version_info < (3, 7) else ""})'

    return _fmt


if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from typing import Protocol
else:  # pragma: no cover (<py38)
    from typing_extensions import Protocol  # noqa


class ToxIniCreator(Protocol):
    def __call__(self, conf: str, override: Optional[Sequence[Override]] = None) -> Config:
        ...


@pytest.fixture
def tox_ini_conf(tmp_path: Path, monkeypatch: MonkeyPatch) -> ToxIniCreator:
    def func(conf: str, override: Optional[Sequence[Override]] = None) -> Config:
        dest = tmp_path / "c"
        dest.mkdir()
        config_file = dest / "tox.ini"
        config_file.write_bytes(conf.encode("utf-8"))
        with monkeypatch.context() as context:
            context.chdir(tmp_path)
        return make_config(
            Parsed(work_dir=dest, override=override or [], config_file=config_file, root_dir=None),
            pos_args=[],
        )

    return func


@pytest.fixture(scope="session")
def demo_pkg_setuptools() -> Path:
    return HERE / "demo_pkg_setuptools"


@pytest.fixture(scope="session")
def demo_pkg_inline() -> Path:
    return HERE / "demo_pkg_inline"
