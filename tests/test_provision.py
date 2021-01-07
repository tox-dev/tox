import json
import os
import sys
from pathlib import Path
from subprocess import check_call
from typing import List, Optional
from zipfile import ZipFile

import pytest
from packaging.requirements import Requirement

from tox.pytest import Index, IndexServer, MonkeyPatch, TempPathFactory, ToxProjectCreator

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution  # type: ignore[attr-defined]
else:  # pragma: no cover (<py38)
    from importlib_metadata import Distribution  # noqa

ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="session")
def tox_wheel(tmp_path_factory: TempPathFactory) -> Path:
    # takes around 3.2s
    package: Optional[Path] = None
    if "TOX_PACKAGE" in os.environ:
        env_tox_pkg = Path(os.environ["TOX_PACKAGE"])
        if env_tox_pkg.exists() and env_tox_pkg.suffix == ".whl":
            package = env_tox_pkg
    if package is None:  # pragma: no cover
        # when we don't get a wheel path injected, build it (for example when running from an IDE)
        package = build_wheel(tmp_path_factory.mktemp("dist"), Path(__file__).parents[1])
    return package


@pytest.fixture(scope="session")
def tox_wheels(tox_wheel: Path, tmp_path_factory: TempPathFactory) -> List[Path]:
    # takes around 1.5s if already cached
    result: List[Path] = [tox_wheel]
    info = tmp_path_factory.mktemp("info")
    with ZipFile(str(tox_wheel), "r") as zip_file:
        zip_file.extractall(path=info)
    dist_info = next((i for i in info.iterdir() if i.suffix == ".dist-info"), None)
    if dist_info is None:  # pragma: no cover
        raise RuntimeError(f"no tox.dist-info inside {tox_wheel}")
    distribution = Distribution.at(dist_info)
    wheel_cache = ROOT / ".wheel_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
    wheel_cache.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-I", "-m", "pip", "download", "-d", str(wheel_cache)]
    for req in distribution.requires:
        requirement = Requirement(req)
        if not requirement.extras:  # pragma: no branch  # we don't need to install any extras (tests/docs/etc)
            cmd.append(req)
    check_call(cmd)
    result.extend(wheel_cache.iterdir())
    return result


@pytest.fixture(scope="session")
def demo_pkg_inline_wheel(tmp_path_factory: TempPathFactory, demo_pkg_inline: Path) -> Path:
    return build_wheel(tmp_path_factory.mktemp("dist"), demo_pkg_inline)


def build_wheel(dist_dir: Path, of: Path) -> Path:
    from build.__main__ import build_package  # noqa

    build_package(str(of), str(dist_dir), distributions=["wheel"])
    package = next(dist_dir.iterdir())
    return package


@pytest.fixture(scope="session")
def pypi_index_self(pypi_server: IndexServer, tox_wheels: List[Path], demo_pkg_inline_wheel: Path) -> Index:
    # takes around 1s
    self_index = pypi_server.create_index("self", "volatile=False")
    self_index.upload(tox_wheels + [demo_pkg_inline_wheel])
    return self_index


def test_provision_requires_nok(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nrequires = pkg-does-not-exist\n setuptools==1\nskipsdist=true\n"
    outcome = tox_project({"tox.ini": ini}).run("c", "-e", "py")
    outcome.assert_failed()
    outcome.assert_out_err(
        r".*will run in automatically provisioned tox, host .* is missing \[requires \(has\)\]:"
        r" pkg-does-not-exist \(N/A\), setuptools==1 \(.*\).*",
        r".*",
        regex=True,
    )


@pytest.mark.integration
@pytest.mark.timeout(60)
def test_provision_requires_ok(
    tox_project: ToxProjectCreator, pypi_index_self: Index, monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    log = tmp_path / "out.log"
    pypi_index_self.use(monkeypatch)
    ini = "[tox]\nrequires = demo-pkg-inline\n setuptools \n[testenv]\npackage=skip"

    outcome = tox_project({"tox.ini": ini}).run("r", "-e", "py", "--result-json", str(log))

    outcome.assert_success()
    with log.open("rt") as file_handler:
        log_report = json.load(file_handler)
    assert "py" in log_report["testenvs"]
