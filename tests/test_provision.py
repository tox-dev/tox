import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from subprocess import check_call
from typing import Iterator, List, Optional
from zipfile import ZipFile

import pytest
from packaging.requirements import Requirement

from tox.pytest import Index, IndexServer, MonkeyPatch, TempPathFactory, ToxProjectCreator

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution  # type: ignore[attr-defined]
else:  # pragma: no cover (<py38)
    from importlib_metadata import Distribution  # noqa

ROOT = Path(__file__).parents[1]


@contextmanager
def elapsed(msg: str) -> Iterator[None]:
    start = time.monotonic()
    try:
        yield
    finally:
        print(f"done in {time.monotonic() - start}s {msg}")


@pytest.fixture(scope="session")
def tox_wheel(tmp_path_factory: TempPathFactory) -> Path:
    with elapsed("acquire current tox wheel"):  # takes around 3.2s on build
        package: Optional[Path] = None
        if "TOX_PACKAGE" in os.environ:
            env_tox_pkg = Path(os.environ["TOX_PACKAGE"])  # pragma: no cover
            if env_tox_pkg.exists() and env_tox_pkg.suffix == ".whl":  # pragma: no cover
                package = env_tox_pkg  # pragma: no cover
        if package is None:
            # when we don't get a wheel path injected, build it (for example when running from an IDE)
            package = build_wheel(tmp_path_factory.mktemp("dist"), Path(__file__).parents[1])  # pragma: no cover
        return package


@pytest.fixture(scope="session")
def tox_wheels(tox_wheel: Path, tmp_path_factory: TempPathFactory) -> List[Path]:
    with elapsed("acquire dependencies for current tox"):  # takes around 1.5s if already cached
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
    with elapsed("start devpi and create index"):  # takes around 1s
        self_index = pypi_server.create_index("self", "volatile=False")
    with elapsed("upload tox and its wheels to devpi"):  # takes around 3.2s on build
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
    pypi_index_self.use(monkeypatch)
    proj = tox_project({"tox.ini": "[tox]\nrequires=demo-pkg-inline\n[testenv]\npackage=skip"})
    log = tmp_path / "out.log"

    # initial run
    result_first = proj.run("r", "--result-json", str(log))
    result_first.assert_success()
    prov_msg = (
        f"ROOT: will run in automatically provisioned tox, host {sys.executable} is missing"
        f" [requires (has)]: demo-pkg-inline (N/A)"
    )
    assert prov_msg in result_first.out

    with log.open("rt") as file_handler:
        log_report = json.load(file_handler)
    assert "py" in log_report["testenvs"]

    # recreate without recreating the provisioned env
    provision_env = result_first.env_conf(".tox")["env_dir"]
    result_recreate_no_pr = proj.run("r", "--recreate", "--no-recreate-provision")
    result_recreate_no_pr.assert_success()
    assert prov_msg in result_recreate_no_pr.out
    assert f"ROOT: remove tox env folder {provision_env}" not in result_recreate_no_pr.out, result_recreate_no_pr.out

    # recreate with recreating the provisioned env
    result_recreate = proj.run("r", "--recreate")
    result_recreate.assert_success()
    assert prov_msg in result_recreate.out
    assert f"ROOT: remove tox env folder {provision_env}" in result_recreate.out, result_recreate.out
