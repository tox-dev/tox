import sys
from contextlib import contextmanager
from pathlib import Path
from stat import S_IWGRP, S_IWOTH, S_IWUSR
from textwrap import dedent
from typing import Callable, Iterator, NamedTuple

import pytest
from packaging.requirements import Requirement
from pytest_mock import MockerFixture

from tox.pytest import TempPathFactory
from tox.util.pep517.frontend import BackendFailed
from tox.util.pep517.via_fresh_subprocess import SubprocessFrontend

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from importlib.metadata import Distribution, EntryPoint  # type: ignore[attr-defined]
else:  # pragma: no cover (<py38)
    from importlib_metadata import Distribution, EntryPoint  # noqa


@pytest.fixture(scope="session")
def frontend_setuptools(tmp_path_factory: TempPathFactory) -> SubprocessFrontend:
    prj = tmp_path_factory.mktemp("proj")
    (prj / "pyproject.toml").write_text(
        '[build-system]\nrequires=["setuptools","wheel"]\nbuild-backend = "setuptools.build_meta"'
    )
    cfg = """
        [metadata]
        name = demo
        version = 1.0

        [options]
        packages = demo
        install_requires =
          requests>2
          magic>3

        [options.entry_points]
        console_scripts =
            demo_exe = demo:a
        """
    (prj / "setup.cfg").write_text(cfg)
    (prj / "setup.py").write_text("from setuptools import setup; setup()")
    demo = prj / "demo"
    demo.mkdir()
    (demo / "__init__.py").write_text("def a(): print('ok')")
    args = SubprocessFrontend.create_args_from_folder(prj)
    return SubprocessFrontend(*args[:-1])


def test_pep517_setuptools_get_requires_for_build_sdist(frontend_setuptools: SubprocessFrontend) -> None:
    result = frontend_setuptools.get_requires_for_build_sdist()
    assert result.requires == ()
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)


def test_pep517_setuptools_get_requires_for_build_wheel(frontend_setuptools: SubprocessFrontend) -> None:
    result = frontend_setuptools.get_requires_for_build_wheel()
    for left, right in zip(result.requires, (Requirement("wheel"),)):
        assert isinstance(left, Requirement)
        assert str(left) == str(right)
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)


def test_pep517_setuptools_prepare_metadata_for_build_wheel(
    frontend_setuptools: SubprocessFrontend, tmp_path: Path
) -> None:
    meta = tmp_path / "meta"
    result = frontend_setuptools.prepare_metadata_for_build_wheel(metadata_directory=meta)
    dist = Distribution.at(str(result.metadata))
    assert dist.entry_points == [EntryPoint(name="demo_exe", value="demo:a", group="console_scripts")]
    assert dist.version == "1.0"
    assert dist.metadata["Name"] == "demo"
    assert [v for k, v in dist.metadata.items() if k == "Requires-Dist"] == ["requests (>2)", "magic (>3)"]
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)

    # call it again regenerates it because frontend always deletes earlier content
    before = result.metadata.stat().st_mtime
    result = frontend_setuptools.prepare_metadata_for_build_wheel(metadata_directory=meta)
    after = result.metadata.stat().st_mtime
    assert after > before


def test_pep517_setuptools_build_sdist(frontend_setuptools: SubprocessFrontend, tmp_path: Path) -> None:
    result = frontend_setuptools.build_sdist(tmp_path)
    sdist = result.sdist
    assert sdist.exists()
    assert sdist.is_file()
    assert sdist.name == "demo-1.0.tar.gz"
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)


def test_pep517_setuptools_build_wheel(frontend_setuptools: SubprocessFrontend, tmp_path: Path) -> None:
    result = frontend_setuptools.build_wheel(tmp_path)
    wheel = result.wheel
    assert wheel.exists()
    assert wheel.is_file()
    assert wheel.name == "demo-1.0-py3-none-any.whl"
    assert isinstance(result.out, str)
    assert isinstance(result.err, str)


def test_pep517_setuptools_exit(frontend_setuptools: SubprocessFrontend) -> None:
    result, out, err = frontend_setuptools.send_cmd("_exit")
    assert isinstance(out, str)
    assert isinstance(err, str)
    assert result == 0


def test_pep517_setuptools_missing_command(frontend_setuptools: SubprocessFrontend) -> None:
    with pytest.raises(BackendFailed):
        frontend_setuptools.send_cmd("missing_command")


def test_pep517_setuptools_exception(frontend_setuptools: SubprocessFrontend) -> None:
    with pytest.raises(BackendFailed) as context:
        frontend_setuptools.send_cmd("build_wheel")
    assert isinstance(context.value.out, str)
    assert isinstance(context.value.err, str)
    assert context.value.exc_type == "TypeError"
    assert context.value.exc_msg == "build_wheel() missing 1 required positional argument: 'wheel_directory'"
    assert context.value.code == 1
    assert context.value.args == ()
    assert repr(context.value)
    assert str(context.value)
    assert repr(context.value) != str(context.value)


def test_pep517_bad_message(frontend_setuptools: SubprocessFrontend, tmp_path: Path) -> None:
    with frontend_setuptools._send_msg("bad_cmd", tmp_path / "a", "{") as status:
        while not status.done:
            pass
    out, err = status.out_err()
    assert out
    assert "Backend: incorrect request to backend: {" in err


def test_pep517_result_missing(frontend_setuptools: SubprocessFrontend, tmp_path: Path, mocker: MockerFixture) -> None:
    class _Result(NamedTuple):
        name: str

    @contextmanager
    def named_temporary_file(prefix: str) -> Iterator[_Result]:
        write = S_IWUSR | S_IWGRP | S_IWOTH
        base = tmp_path / prefix
        result = base.with_suffix(".json")
        result.write_text("")
        result.chmod(result.stat().st_mode & ~write)  # force json write to fail due to R/O
        patch = mocker.patch("tox.util.pep517.frontend.Path.exists", return_value=False)  # make it missing
        try:
            yield _Result(str(base))
        finally:
            patch.stop()
            result.chmod(result.stat().st_mode | write)  # cleanup
            result.unlink()

    mocker.patch("tox.util.pep517.frontend.NamedTemporaryFile", named_temporary_file)
    with pytest.raises(BackendFailed) as context:
        frontend_setuptools.send_cmd("_exit")
    exc = context.value
    assert exc.exc_msg == f"Backend response file {tmp_path / 'pep517__exit-.json'} is missing"
    assert exc.exc_type == "RuntimeError"
    assert exc.code == 1
    assert "Traceback" in exc.err
    assert "PermissionError" in exc.err


@pytest.fixture
def local_builder(tmp_path: Path) -> Callable[[str], Path]:
    def _f(content: str) -> Path:
        toml = '[build-system]\nrequires=[]\nbuild-backend = "build_tester"\nbackend-path=["."]'
        (tmp_path / "pyproject.toml").write_text(toml)
        (tmp_path / "build_tester.py").write_text(dedent(content))
        return tmp_path

    return _f


def test_pep517_missing_backend(local_builder: Callable[[str], Path]) -> None:
    tmp_path = local_builder("")
    toml = tmp_path / "pyproject.toml"
    toml.write_text('[build-system]\nrequires=[]\nbuild-backend = "build_tester"')
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])
    with pytest.raises(BackendFailed) as context:
        fronted.build_wheel(tmp_path / "wheel")
    exc = context.value
    assert exc.exc_type == "RuntimeError"
    assert exc.code == 1
    assert "failed to start backend" in exc.err
    assert "ModuleNotFoundError: No module named " in exc.err


@pytest.mark.parametrize("cmd", ["build_wheel", "build_sdist"])
def test_pep517_missing_required_cmd(cmd: str, local_builder: Callable[[str], Path]) -> None:
    tmp_path = local_builder("")
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])

    with pytest.raises(BackendFailed) as context:
        getattr(fronted, cmd)(tmp_path)
    exc = context.value
    assert f"has no attribute '{cmd}'" in exc.exc_msg
    assert exc.exc_type == "MissingCommand"


def test_pep517_empty_pyproject(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[build-system]")
    root, backend_paths, backend_module, backend_obj, requires, _ = SubprocessFrontend.create_args_from_folder(tmp_path)
    assert root == tmp_path
    assert backend_paths == ()
    assert backend_module == "setuptools.build_meta"
    assert backend_obj == "__legacy__"
    for left, right in zip(requires, (Requirement("setuptools>=40.8.0"), Requirement("wheel"))):
        assert isinstance(left, Requirement)
        assert str(left) == str(right)


def test_pep517_backend_no_prepare_wheel(tmp_path: Path, demo_pkg_inline: Path) -> None:
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(demo_pkg_inline)[:-1])
    result = fronted.prepare_metadata_for_build_wheel(tmp_path)
    assert result.metadata.name == "demo_pkg_inline-1.0.0.dist-info"


def test_pep517_backend_build_sdist_demo_pkg_inline(tmp_path: Path, demo_pkg_inline: Path) -> None:
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(demo_pkg_inline)[:-1])
    result = fronted.build_sdist(sdist_directory=tmp_path)
    assert result.sdist == tmp_path / "demo_pkg_inline-1.0.0.tar.gz"


def test_pep517_backend_obj(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        dedent(
            """
        [build-system]
        requires=[]
        build-backend = "build.api:backend:"
        backend-path=["."]
        """
        )
    )
    build = tmp_path / "build"
    build.mkdir()
    (build / "__init__.py").write_text("")
    (build / "api.py").write_text(
        dedent(
            """
        class A:
            def get_requires_for_build_sdist(self, config_settings=None):
                return ["a"]

        backend = A()
        """
        )
    )
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])
    result = fronted.get_requires_for_build_sdist()
    for left, right in zip(result.requires, (Requirement("a"),)):
        assert isinstance(left, Requirement)
        assert str(left) == str(right)


@pytest.mark.parametrize("of_type", ["wheel", "sdist"])
def test_pep517_get_requires_for_build_missing(of_type: str, local_builder: Callable[[str], Path]) -> None:
    tmp_path = local_builder("")
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])
    result = getattr(fronted, f"get_requires_for_build_{of_type}")()
    assert result.requires == ()


@pytest.mark.parametrize("of_type", ["sdist", "wheel"])
def test_pep517_bad_return_type_get_requires_for_build(of_type: str, local_builder: Callable[[str], Path]) -> None:
    tmp_path = local_builder(f"def get_requires_for_build_{of_type}(config_settings=None): return 1")
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])

    with pytest.raises(BackendFailed) as context:
        getattr(fronted, f"get_requires_for_build_{of_type}")()

    exc = context.value
    msg = f"'get_requires_for_build_{of_type}' on 'build_tester' returned 1 but expected type 'list of string'"
    assert exc.exc_msg == msg
    assert exc.exc_type == "TypeError"


def test_pep517_bad_return_type_build_sdist(local_builder: Callable[[str], Path]) -> None:
    tmp_path = local_builder("def build_sdist(sdist_directory, config_settings=None): return 1")
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])

    with pytest.raises(BackendFailed) as context:
        fronted.build_sdist(tmp_path)

    exc = context.value
    assert exc.exc_msg == f"'build_sdist' on 'build_tester' returned 1 but expected type {str!r}"
    assert exc.exc_type == "TypeError"


def test_pep517_bad_return_type_build_wheel(local_builder: Callable[[str], Path]) -> None:
    txt = "def build_wheel(wheel_directory, config_settings=None, metadata_directory=None): return 1"
    tmp_path = local_builder(txt)
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])

    with pytest.raises(BackendFailed) as context:
        fronted.build_wheel(tmp_path)

    exc = context.value
    assert exc.exc_msg == f"'build_wheel' on 'build_tester' returned 1 but expected type {str!r}"
    assert exc.exc_type == "TypeError"


def test_pep517_bad_return_type_prepare_metadata_for_build_wheel(local_builder: Callable[[str], Path]) -> None:
    tmp_path = local_builder("def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None): return 1")
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])

    with pytest.raises(BackendFailed) as context:
        fronted.prepare_metadata_for_build_wheel(tmp_path / "meta")

    exc = context.value
    assert exc.exc_type == "TypeError"
    assert exc.exc_msg == f"'prepare_metadata_for_build_wheel' on 'build_tester' returned 1 but expected type {str!r}"


def test_pep517_prepare_metadata_for_build_wheel_meta_is_root(local_builder: Callable[[str], Path]) -> None:
    tmp_path = local_builder("def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None): return 1")
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])

    with pytest.raises(RuntimeError) as context:
        fronted.prepare_metadata_for_build_wheel(tmp_path)

    assert str(context.value) == f"the project root and the metadata directory can't be the same {tmp_path}"


def test_pep517_no_wheel_prepare_metadata_for_build_wheel(local_builder: Callable[[str], Path]) -> None:
    txt = "def build_wheel(wheel_directory, config_settings=None, metadata_directory=None): return 'out'"
    tmp_path = local_builder(txt)
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])

    with pytest.raises(RuntimeError, match="missing wheel file return by backed *"):
        fronted.prepare_metadata_for_build_wheel(tmp_path / "meta")


def test_pep517_bad_wheel_prepare_metadata_for_build_wheel(local_builder: Callable[[str], Path]) -> None:
    txt = """
    import sys
    from pathlib import Path
    from zipfile import ZipFile

    def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
        path = Path(wheel_directory) / "out"
        with ZipFile(str(path), "w") as zip_file_handler:
            pass
        print(f"created wheel {path}")
        return path.name
    """
    tmp_path = local_builder(txt)
    fronted = SubprocessFrontend(*SubprocessFrontend.create_args_from_folder(tmp_path)[:-1])

    with pytest.raises(RuntimeError, match="no .dist-info found inside generated wheel*"):
        fronted.prepare_metadata_for_build_wheel(tmp_path / "meta")
