from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Iterator, Protocol, Sequence
from unittest.mock import patch
from uuid import uuid4

import pytest
from distlib.scripts import ScriptMaker
from filelock import FileLock
from virtualenv import cli_run

from tox.config.cli.parser import Parsed
from tox.config.main import Config
from tox.config.source import discover_source
from tox.tox_env.python.api import PythonInfo, VersionInfo
from tox.tox_env.python.virtual_env.api import VirtualEnv

if TYPE_CHECKING:
    from build import DistributionType
    from pytest_mock import MockerFixture

    from tox.config.loader.api import Override

pytest_plugins = "tox.pytest"
HERE = Path(__file__).absolute().parent


@pytest.fixture(scope="session")
def value_error() -> Callable[[str], str]:
    def _fmt(msg: str) -> str:
        return f'ValueError("{msg}"{"," if sys.version_info < (3, 7) else ""})'

    return _fmt


collect_ignore = []
if sys.implementation.name == "pypy":
    # time-machine causes segfaults on PyPy
    collect_ignore.append("util/test_spinner.py")


class ToxIniCreator(Protocol):
    def __call__(self, conf: str, override: Sequence[Override] | None = None) -> Config: ...


@pytest.fixture
def tox_ini_conf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ToxIniCreator:
    def func(conf: str, override: Sequence[Override] | None = None) -> Config:
        dest = tmp_path / "c"
        dest.mkdir()
        config_file = dest / "tox.ini"
        config_file.write_bytes(conf.encode("utf-8"))
        with monkeypatch.context() as context:
            context.chdir(tmp_path)
        source = discover_source(config_file, None)

        return Config.make(
            Parsed(work_dir=dest, override=override or [], config_file=config_file, root_dir=None),
            pos_args=[],
            source=source,
        )

    return func


@pytest.fixture(scope="session")
def demo_pkg_setuptools() -> Path:
    return HERE / "demo_pkg_setuptools"


@pytest.fixture(scope="session")
def demo_pkg_inline() -> Iterator[Path]:
    demo_path = HERE / "demo_pkg_inline"
    with FileLock(f"{demo_path}.lock"):
        yield demo_path


@pytest.fixture
def patch_prev_py(mocker: MockerFixture) -> Callable[[bool], tuple[str, str]]:
    def _func(has_prev: bool) -> tuple[str, str]:
        ver = sys.version_info[0:2]
        prev_ver = "".join(str(i) for i in (ver[0], ver[1] - 1))
        prev_py = f"py{prev_ver}"
        impl = sys.implementation.name.lower()

        def get_python(self: VirtualEnv, base_python: list[str]) -> PythonInfo | None:  # noqa: ARG001
            if base_python[0] == "py31" or (base_python[0] == prev_py and not has_prev):
                return None
            raw = list(sys.version_info)
            if base_python[0] == prev_py:
                raw[1] -= 1  # type: ignore[operator]
            ver_info = VersionInfo(*raw)  # type: ignore[arg-type]
            return PythonInfo(
                implementation=impl,
                version_info=ver_info,
                version="",
                is_64=True,
                platform=sys.platform,
                extra={"executable": Path(sys.executable)},
            )

        mocker.patch.object(VirtualEnv, "_get_python", get_python)
        return prev_ver, impl

    return _func


@pytest.fixture(scope="session", autouse=True)
def _do_not_share_virtualenv_for_parallel_runs(tmp_path_factory: pytest.TempPathFactory, worker_id: str) -> None:
    # virtualenv uses locks to manage access to its cache, when running with xdist this may throw off test timings
    if worker_id != "master":  # pragma: no branch
        temp_app_data = str(tmp_path_factory.mktemp(f"virtualenv-app-{worker_id}"))  # pragma: no cover
        os.environ["VIRTUALENV_APP_DATA"] = temp_app_data  # pragma: no cover
        seed_env_folder = str(tmp_path_factory.mktemp(f"seed-cache-{worker_id}"))  # pragma: no cover
        args = [seed_env_folder, "--without-pip", "--activators", ""]  # pragma: no cover
        cli_run(args, setup_logging=False)  # pragma: no cover


@pytest.fixture(scope="session")
def fake_exe_on_path(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Path]:
    tmp_path = Path(tmp_path_factory.mktemp("a"))
    cmd_name = uuid4().hex
    maker = ScriptMaker(None, str(tmp_path))
    maker.set_mode = True
    maker.variants = {""}
    maker.make(f"{cmd_name} = b:c")
    with patch.dict(os.environ, {"PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"}):
        yield tmp_path / cmd_name


@pytest.fixture(scope="session")
def demo_pkg_inline_wheel(tmp_path_factory: pytest.TempPathFactory, demo_pkg_inline: Path) -> Path:
    return build_pkg(tmp_path_factory.mktemp("dist"), demo_pkg_inline, ["wheel"])


def build_pkg(dist_dir: Path, of: Path, distributions: Sequence[DistributionType], isolation: bool = True) -> Path:
    from build.__main__ import build_package  # noqa: PLC0415,PLC2701

    build_package(str(of), str(dist_dir), distributions=distributions, isolation=isolation)
    return next(dist_dir.iterdir())


@pytest.fixture(scope="session")
def pkg_builder() -> Callable[[Path, Path, Sequence[DistributionType], bool], Path]:
    return build_pkg
