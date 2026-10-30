from __future__ import annotations

import ctypes
import os
import stat
import sys
from ctypes import wintypes
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import pytest

from tox.util.venv_redirect import forget_venv_redirect, record_venv_redirect, release_venv_redirect

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_record_creates_redirect(root: Path) -> None:
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (root / ".venv").read_text(encoding="utf-8") == ".tox/dev\n"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
def test_record_creates_private_redirect(root: Path) -> None:
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert stat.S_IMODE((root / ".venv").stat().st_mode) & 0o077 == 0


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / ".tox").mkdir()
    return tmp_path


def _is_ours(root: Path) -> Callable[[Path], bool]:
    return lambda path: path.is_relative_to(root / ".tox")


def test_record_env_outside_root_is_absolute(root: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    outside: Final[Path] = tmp_path_factory.mktemp("elsewhere") / "dev"

    record_venv_redirect(root, outside, lambda _: True)

    assert (root / ".venv").read_text(encoding="utf-8") == f"{outside}\n"


@pytest.mark.parametrize(
    "existing",
    [
        pytest.param(".tox/3.13\n", id="trailing_newline"),
        pytest.param(".tox/3.13", id="no_trailing_newline"),
        pytest.param(".tox/3.13\r\n", id="crlf"),
        pytest.param("./.tox/../.tox/3.13\n", id="unnormalized"),
    ],
)
def test_record_replaces_own_redirect(root: Path, existing: str) -> None:
    (root / ".venv").write_bytes(existing.encode())

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (root / ".venv").read_text(encoding="utf-8") == ".tox/dev\n"


@pytest.mark.parametrize(
    "existing",
    [
        pytest.param("../shared\n", id="foreign"),
        pytest.param("", id="empty"),
        pytest.param("\n", id="newline_only"),
        pytest.param(".tox/../../escape\n", id="escapes_work_dir"),
    ],
)
def test_record_keeps_foreign_redirect(root: Path, created_redirect: Path, existing: str) -> None:
    created_redirect.write_text(existing, encoding="utf-8")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert created_redirect.read_text(encoding="utf-8") == existing


@pytest.fixture
def created_redirect(root: Path) -> Path:
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))
    redirect: Final[Path] = root / ".venv"
    assert redirect.read_text(encoding="utf-8") == ".tox/dev\n"
    return redirect


def test_record_keeps_undecodable_redirect(root: Path, created_redirect: Path) -> None:
    created_redirect.write_bytes(b"\xff\xfe.tox/3.13\n")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert created_redirect.read_bytes() == b"\xff\xfe.tox/3.13\n"


def test_record_keeps_venv_directory(root: Path, created_redirect: Path) -> None:
    created_redirect.unlink()
    created_redirect.mkdir()

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert created_redirect.is_dir()


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_record_keeps_venv_symlink(root: Path, created_redirect: Path) -> None:
    created_redirect.unlink()
    created_redirect.symlink_to(root / ".tox" / "3.13")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert created_redirect.readlink() == root / ".tox" / "3.13"


def test_record_same_target_does_not_write(root: Path, created_redirect: Path) -> None:
    os.utime(created_redirect, ns=(1_000_000_000, 1_000_000_000))

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert created_redirect.stat().st_mtime_ns == 1_000_000_000


def test_record_warns_when_root_missing(root: Path, caplog: pytest.LogCaptureFixture) -> None:
    record_venv_redirect(root / "missing", root / ".tox" / "dev", _is_ours(root))

    assert "could not point" in caplog.text


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory-relative replacement")
def test_record_keeps_redirect_if_replace_fails(
    root: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    redirect: Final[Path] = root / ".venv"
    redirect.write_text(".tox/3.13\n", encoding="utf-8")
    mocker.patch.object(os, "replace", autospec=True, side_effect=PermissionError("read-only"))

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (
        redirect.read_text(encoding="utf-8"),
        sorted(path.name for path in root.iterdir()),
        "could not point" in caplog.text,
    ) == (".tox/3.13\n", [".tox", ".venv"], True)


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_record_stays_in_root_swapped_after_check(root: Path, swap_root: _SwapRoot) -> None:
    (root / ".venv").write_text(".tox/3.13\n", encoding="utf-8")

    record_venv_redirect(root, root / ".tox" / "dev", lambda _: swap_root.swap() is None)

    assert (swap_root.other / ".venv").read_text(encoding="utf-8") == "../shared\n"
    assert (swap_root.moved / ".venv").read_text(encoding="utf-8") == ".tox/dev\n"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows directory sharing")
@pytest.mark.parametrize(
    "directory_parts",
    [pytest.param(("parent", "project"), id="root"), pytest.param(("parent",), id="parent")],
)
def test_record_windows_blocks_directory_rename_during_check(tmp_path: Path, directory_parts: tuple[str, ...]) -> None:
    project: Final[Path] = tmp_path / "parent" / "project"
    project.mkdir(parents=True)
    (project / ".venv").write_text(".tox/old\n", encoding="utf-8")
    moved: Final[Path] = tmp_path / "moved"

    def swap(_: Path) -> bool:
        with pytest.raises(PermissionError):
            tmp_path.joinpath(*directory_parts).rename(moved)
        return True

    record_venv_redirect(project, project / ".tox" / "dev", swap)

    assert ((project / ".venv").read_text(encoding="utf-8"), moved.exists()) == (".tox/dev\n", False)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows project reparse points")
def test_record_windows_refuses_project_symlink(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    target: Final[Path] = tmp_path / "other"
    target.mkdir()
    (target / ".venv").write_text(".tox/old\n", encoding="utf-8")
    project: Final[Path] = tmp_path / "project"
    project.symlink_to(target, target_is_directory=True)

    record_venv_redirect(project, project / ".tox" / "dev", lambda _: True)

    assert ((target / ".venv").read_text(encoding="utf-8"), "could not point" in caplog.text) == (
        ".tox/old\n",
        True,
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows directory handles")
def test_record_windows_warns_if_directory_info_fails(
    root: Path, windows_kernel32: ctypes.CDLL, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    redirect: Final[Path] = root / ".venv"
    redirect.write_text(".tox/old\n", encoding="utf-8")
    mocker.patch.object(windows_kernel32, "GetFileInformationByHandleEx", return_value=0)
    mocker.patch.object(ctypes, "get_last_error", return_value=5)

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (redirect.read_text(encoding="utf-8"), "[WinError 5]" in caplog.text) == (".tox/old\n", True)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows directory handles")
def test_record_windows_warns_if_directory_close_fails(
    root: Path, windows_kernel32: ctypes.CDLL, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    redirect: Final[Path] = root / ".venv"
    redirect.write_text(".tox/old\n", encoding="utf-8")
    close_handle: Final[Callable[[int], int]] = windows_kernel32.CloseHandle
    close_handle.argtypes = [wintypes.HANDLE]
    close_handle.restype = wintypes.BOOL

    def report_failed_close(handle: int) -> int:
        assert close_handle(handle)
        return 0

    mocker.patch.object(windows_kernel32, "CloseHandle", side_effect=report_failed_close)
    mocker.patch.object(ctypes, "get_last_error", return_value=5)

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (redirect.read_text(encoding="utf-8"), "could not point" in caplog.text) == (".tox/dev\n", True)


@pytest.fixture
def windows_kernel32(mocker: MockerFixture) -> ctypes.CDLL:
    kernel32: Final[ctypes.CDLL] = ctypes.WinDLL(  # type: ignore[attr-defined]  # Windows-only API.
        "kernel32",
        use_last_error=True,
    )
    mocker.patch("tox.util.venv_redirect.ctypes.WinDLL", return_value=kernel32)
    return kernel32


@pytest.fixture
def swap_root(root: Path, tmp_path_factory: pytest.TempPathFactory) -> _SwapRoot:
    other: Final[Path] = tmp_path_factory.mktemp("other") / "project"
    other.mkdir()
    (other / ".venv").write_text("../shared\n", encoding="utf-8")
    moved: Final[Path] = other.with_name("moved")

    def swap() -> None:
        root.rename(moved)
        root.symlink_to(other)

    return _SwapRoot(swap=swap, moved=moved, other=other)


@dataclass(frozen=True, slots=True, kw_only=True)
class _SwapRoot:
    swap: Callable[[], None]
    moved: Path
    other: Path


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_record_refuses_directory_link_before_open(linked_directory: _LinkedDirectory) -> None:
    record_venv_redirect(linked_directory.project, linked_directory.project / ".tox" / "lint", lambda _: True)

    assert (
        linked_directory.original.read_text(encoding="utf-8"),
        linked_directory.foreign.read_text(encoding="utf-8"),
    ) == (
        ".tox/dev\n",
        "../shared\n",
    )


@pytest.fixture(params=[pytest.param(False, id="root"), pytest.param(True, id="parent")])
def linked_directory(
    root: Path, tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> _LinkedDirectory:
    project: Final[Path] = root / "project"
    project.mkdir()
    outside: Final[Path] = tmp_path_factory.mktemp("other")
    foreign: Final[Path] = outside / "project" / ".venv"
    foreign.parent.mkdir()
    foreign.write_text("../shared\n", encoding="utf-8")
    record_venv_redirect(project, project / ".tox" / "dev", lambda _: True)
    moved: Final[Path] = root.with_name(f"{root.name}-moved") if request.param else root / "moved"
    if request.param:
        root.rename(moved)
        root.symlink_to(outside)
    else:
        project.rename(moved)
        project.symlink_to(outside / "project")

    original: Final[Path] = moved / "project" / ".venv" if request.param else moved / ".venv"
    return _LinkedDirectory(project=project, original=original, foreign=foreign)


@dataclass(frozen=True, slots=True, kw_only=True)
class _LinkedDirectory:
    project: Path
    original: Path
    foreign: Path


def test_record_keeps_target_of_symlink_swapped_in_after_check(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    foreign: Final[Path] = tmp_path_factory.mktemp("other") / ".venv"
    foreign.write_text("../shared\n", encoding="utf-8")

    def swap(_: Path) -> bool:
        (root / ".venv").unlink()
        (root / ".venv").symlink_to(foreign)
        return True

    (root / ".venv").write_text(".tox/3.13\n", encoding="utf-8")

    record_venv_redirect(root, root / ".tox" / "dev", swap)

    assert (foreign.read_text(encoding="utf-8"), (root / ".venv").read_text(encoding="utf-8")) == (
        "../shared\n",
        ".tox/dev\n",
    )


def test_record_keeps_target_of_hard_link_swapped_in_after_check(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside: Final[Path] = tmp_path_factory.mktemp("other") / "target"
    outside.write_text("keep\n", encoding="utf-8")
    redirect: Final[Path] = root / ".venv"
    redirect.write_text(".tox/3.13\n", encoding="utf-8")

    def swap(_: Path) -> bool:
        redirect.unlink()
        os.link(outside, redirect)
        return True

    record_venv_redirect(root, root / ".tox" / "dev", swap)

    assert (outside.read_text(encoding="utf-8"), redirect.read_text(encoding="utf-8")) == ("keep\n", ".tox/dev\n")


def test_forget_removes_redirect_to_env(root: Path) -> None:
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    forget_venv_redirect(root, root / ".tox" / "dev")

    assert not (root / ".venv").exists()


def test_forget_keeps_redirect_to_other_env(root: Path) -> None:
    record_venv_redirect(root, root / ".tox" / "3.13", _is_ours(root))
    forget_venv_redirect(root, root / ".tox" / "3.13")
    assert not (root / ".venv").exists()
    record_venv_redirect(root, root / ".tox" / "3.13", _is_ours(root))

    forget_venv_redirect(root, root / ".tox" / "dev")

    assert (root / ".venv").read_text(encoding="utf-8") == ".tox/3.13\n"


def test_forget_after_missing_root_is_created(root: Path) -> None:
    missing: Final[Path] = root / "missing"
    forget_venv_redirect(missing, missing / ".tox" / "dev")
    missing.mkdir()
    (missing / ".venv").write_text(".tox/dev\n", encoding="utf-8")

    forget_venv_redirect(missing, missing / ".tox" / "dev")

    assert not (missing / ".venv").exists()


@pytest.mark.parametrize(
    ("target", "released"),
    [pytest.param(".tox/lint", True, id="ours"), pytest.param("../shared", False, id="foreign")],
)
def test_release_redirect_only_when_ours(root: Path, target: str, released: bool) -> None:
    (root / ".venv").write_text(f"{target}\n", encoding="utf-8")

    outcome: Final[bool] = release_venv_redirect(root / ".venv", _is_ours(root))

    assert (outcome, (root / ".venv").exists()) == (released, not released)


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_release_stays_in_directory_swapped_after_check(root: Path, swap_root: _SwapRoot) -> None:
    (root / ".venv").write_text(".tox/lint\n", encoding="utf-8")

    assert release_venv_redirect(root / ".venv", lambda _: swap_root.swap() is None)

    assert (swap_root.other / ".venv").read_text(encoding="utf-8") == "../shared\n"
    assert not (swap_root.moved / ".venv").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows directory sharing")
def test_release_windows_blocks_root_rename_before_unlink(root: Path) -> None:
    redirect: Final[Path] = root / ".venv"
    redirect.write_text(".tox/lint\n", encoding="utf-8")
    moved: Final[Path] = root.with_name(f"{root.name}-moved")

    def try_swap(_: Path) -> bool:
        with pytest.raises(PermissionError):
            root.rename(moved)
        return True

    assert (release_venv_redirect(redirect, try_swap), redirect.exists(), moved.exists()) == (True, False, False)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows temporary replacement")
def test_record_windows_removes_temporary_after_failed_replace(root: Path, caplog: pytest.LogCaptureFixture) -> None:
    redirect: Final[Path] = root / ".venv"
    redirect.write_text(".tox/old\n", encoding="utf-8")

    with redirect.open(encoding="utf-8"):
        record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (
        redirect.read_text(encoding="utf-8"),
        sorted(path.name for path in root.iterdir()),
        "could not point" in caplog.text,
    ) == (
        ".tox/old\n",
        [".tox", ".venv"],
        True,
    )


def test_release_without_directory(root: Path) -> None:
    assert release_venv_redirect(root / "missing" / ".venv", _is_ours(root)) is False
