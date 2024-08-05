from __future__ import annotations

import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from subprocess import check_call
from typing import TYPE_CHECKING, Callable, Iterator
from unittest import mock
from zipfile import ZipFile

import pytest
from filelock import FileLock
from packaging.requirements import Requirement

if TYPE_CHECKING:
    from devpi_process import Index, IndexServer

    from tox.pytest import MonkeyPatch, TempPathFactory, ToxProjectCreator

from importlib.metadata import Distribution

ROOT = Path(__file__).parents[1]


@contextmanager
def elapsed(msg: str) -> Iterator[None]:
    start = time.monotonic()
    try:
        yield
    finally:
        print(f"done in {time.monotonic() - start}s {msg}")  # noqa: T201


@pytest.fixture(scope="session")
def tox_wheel(
    tmp_path_factory: TempPathFactory,
    worker_id: str,
    pkg_builder: Callable[[Path, Path, list[str], bool], Path],
) -> Path:
    if worker_id == "master":  # if not running under xdist we can just return
        return _make_tox_wheel(tmp_path_factory, pkg_builder)  # pragma: no cover
    # otherwise we need to ensure only one worker creates the wheel, and the rest reuses
    root_tmp_dir = tmp_path_factory.getbasetemp().parent
    cache_file = root_tmp_dir / "tox_wheel.json"
    with FileLock(f"{cache_file}.lock"):
        if cache_file.is_file():
            data = Path(json.loads(cache_file.read_text()))  # pragma: no cover
        else:
            data = _make_tox_wheel(tmp_path_factory, pkg_builder)
            cache_file.write_text(json.dumps(str(data)))
    return data


def _make_tox_wheel(
    tmp_path_factory: TempPathFactory,
    pkg_builder: Callable[[Path, Path, list[str], bool], Path],
) -> Path:
    with elapsed("acquire current tox wheel"):  # takes around 3.2s on build
        into = tmp_path_factory.mktemp("dist")  # pragma: no cover
        from tox.version import version_tuple  # noqa: PLC0415

        _patch_version = version_tuple[2]
        if isinstance(_patch_version, str) and _patch_version[:3] == "dev":
            # Version is in the form of 1.23.dev456, we need to increment the 456 part
            version = f"{version_tuple[0]}.{version_tuple[1]}.dev{int(_patch_version[3:]) + 1}"
        else:
            version = f"{version_tuple[0]}.{version_tuple[1]}.{int(_patch_version) + 1}"

        with mock.patch.dict(os.environ, {"SETUPTOOLS_SCM_PRETEND_VERSION": version}):
            return pkg_builder(into, Path(__file__).parents[1], ["wheel"], False)  # pragma: no cover


@pytest.fixture(scope="session")
def tox_wheels(tox_wheel: Path, tmp_path_factory: TempPathFactory) -> list[Path]:
    with elapsed("acquire dependencies for current tox"):  # takes around 1.5s if already cached
        result: list[Path] = [tox_wheel]
        info = tmp_path_factory.mktemp("info")
        with ZipFile(str(tox_wheel), "r") as zip_file:
            zip_file.extractall(path=info)
        dist_info = next((i for i in info.iterdir() if i.suffix == ".dist-info"), None)
        if dist_info is None:  # pragma: no cover
            msg = f"no tox.dist-info inside {tox_wheel}"
            raise RuntimeError(msg)
        distribution = Distribution.at(dist_info)
        wheel_cache = ROOT / ".wheel_cache" / f"{sys.version_info.major}.{sys.version_info.minor}"
        wheel_cache.mkdir(parents=True, exist_ok=True)
        cmd = [sys.executable, "-I", "-m", "pip", "download", "-d", str(wheel_cache)]
        assert distribution.requires is not None
        for req in distribution.requires:
            requirement = Requirement(req)
            if not requirement.extras:  # pragma: no branch  # we don't need to install any extras (tests/docs/etc)
                cmd.append(req)
        check_call(cmd)
        result.extend(wheel_cache.iterdir())
        return result


@pytest.fixture(scope="session")
def pypi_index_self(pypi_server: IndexServer, tox_wheels: list[Path], demo_pkg_inline_wheel: Path) -> Index:
    with elapsed("start devpi and create index"):  # takes around 1s
        self_index = pypi_server.create_index("self", "volatile=False")
    with elapsed("upload tox and its wheels to devpi"):  # takes around 3.2s on build
        self_index.upload(*tox_wheels, demo_pkg_inline_wheel)
    return self_index


@pytest.fixture
def _pypi_index_self(pypi_index_self: Index, monkeypatch: MonkeyPatch) -> None:
    pypi_index_self.use()
    monkeypatch.setenv("PIP_INDEX_URL", pypi_index_self.url)
    monkeypatch.setenv("PIP_RETRIES", str(2))
    monkeypatch.setenv("PIP_TIMEOUT", str(5))


def test_provision_requires_nok(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nrequires = pkg-does-not-exist\n setuptools==1\nskipsdist=true\n"
    outcome = tox_project({"tox.ini": ini}).run("c", "-e", "py")
    outcome.assert_failed()
    outcome.assert_out_err(
        r".*will run in automatically provisioned tox, host .* is missing \[requires \(has\)\]:"
        r" pkg-does-not-exist, setuptools==1 \(.*\).*",
        r".*",
        regex=True,
    )


@pytest.mark.integration
@pytest.mark.usefixtures("_pypi_index_self")
def test_provision_requires_ok(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    proj = tox_project({"tox.ini": "[tox]\nrequires=demo-pkg-inline\n[testenv]\npackage=skip"})
    log = tmp_path / "out.log"

    # initial run
    result_first = proj.run("r", "--result-json", str(log))
    result_first.assert_success()
    prov_msg = (
        f"ROOT: will run in automatically provisioned tox, host {sys.executable} is missing"
        f" [requires (has)]: demo-pkg-inline"
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


@pytest.mark.integration
@pytest.mark.usefixtures("_pypi_index_self")
def test_provision_platform_check(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nrequires=demo-pkg-inline\n[testenv]\npackage=skip\n[testenv:.tox]\nplatform=wrong_platform"
    proj = tox_project({"tox.ini": ini})

    result = proj.run("r")
    result.assert_failed(-2)
    msg = f"cannot provision tox environment .tox because platform {sys.platform} does not match wrong_platform"
    assert msg in result.out


def test_provision_no_recreate(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nrequires = p\nskipsdist=true\n"
    result = tox_project({"tox.ini": ini}).run("c", "-e", "py", "--no-provision")
    result.assert_failed()
    assert f"provisioning explicitly disabled within {sys.executable}, but is missing [requires (has)]: p" in result.out


def test_provision_no_recreate_json(tox_project: ToxProjectCreator) -> None:
    ini = "[tox]\nrequires = p\nskipsdist=true\n"
    project = tox_project({"tox.ini": ini})
    result = project.run("c", "-e", "py", "--no-provision", "out.json")
    result.assert_failed()
    msg = (
        f"provisioning explicitly disabled within {sys.executable}, "
        f"but is missing [requires (has)]: p and wrote to out.json"
    )
    assert msg in result.out
    with (project.path / "out.json").open() as file_handler:
        requires = json.load(file_handler)
    assert requires == {"minversion": None, "requires": ["p", "tox"]}


@pytest.mark.integration
@pytest.mark.usefixtures("_pypi_index_self")
@pytest.mark.parametrize("plugin_testenv", ["testenv", "testenv:a"])
def test_provision_plugin_runner(tox_project: ToxProjectCreator, tmp_path: Path, plugin_testenv: str) -> None:
    """Ensure that testenv runner doesn't affect the provision env."""
    log = tmp_path / "out.log"
    proj = tox_project(
        {"tox.ini": f"[tox]\nrequires=demo-pkg-inline\nlabels=l=py\n[{plugin_testenv}]\nrunner=example"},
    )
    prov_msg = (
        f"ROOT: will run in automatically provisioned tox, host {sys.executable} is missing"
        f" [requires (has)]: demo-pkg-inline"
    )

    result_env = proj.run("r", "-e", "py", "--result-json", str(log))
    result_env.assert_success()
    assert prov_msg in result_env.out

    result_label = proj.run("r", "-m", "l", "--result-json", str(log))
    result_label.assert_success()
    assert prov_msg in result_label.out


@pytest.mark.integration
def test_provision_plugin_runner_in_provision(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    """Ensure that provision environment can be explicitly configured."""
    log = tmp_path / "out.log"
    proj = tox_project({"tox.ini": "[tox]\nrequires=somepkg123xyz\n[testenv:.tox]\nrunner=example"})
    with pytest.raises(KeyError, match="example"):
        proj.run("r", "-e", "py", "--result-json", str(log))


@pytest.mark.integration
@pytest.mark.usefixtures("_pypi_index_self")
@pytest.mark.parametrize("relative_path", [True, False], ids=["relative", "absolute"])
def test_provision_conf_file(tox_project: ToxProjectCreator, tmp_path: Path, relative_path: bool) -> None:
    ini = "[tox]\nrequires = demo-pkg-inline\nskipsdist=true\n"
    project = tox_project({"tox.ini": ini}, prj_path=tmp_path / "sub")
    conf_path = str(Path(project.path.name) / "tox.ini") if relative_path else str(project.path / "tox.ini")
    result = project.run("c", "--conf", conf_path, "-e", "py", from_cwd=tmp_path)
    result.assert_success()


@pytest.mark.parametrize("subcommand", ["r", "p", "de", "l", "d", "c", "q", "e", "le"])
def test_provision_default_arguments_exists(tox_project: ToxProjectCreator, subcommand: str) -> None:
    ini = r"""
    [tox]
    requires =
        tox<4.14
    [testenv]
    package = skip
    """
    project = tox_project({"tox.ini": ini})
    project.patch_execute(lambda r: 0 if "install" in r.run_id else None)
    outcome = project.run(subcommand)
    for argument in ["result_json", "hash_seed", "discover", "list_dependencies"]:
        assert hasattr(outcome.state.conf.options, argument)
