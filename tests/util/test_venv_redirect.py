from __future__ import annotations

import os
import sys
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


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / ".tox").mkdir()
    return tmp_path


def _is_ours(root: Path) -> Callable[[Path], bool]:
    return lambda path: path.is_relative_to(root / ".tox")


def test_record_env_outside_root_is_absolute(root: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    outside = tmp_path_factory.mktemp("elsewhere") / "dev"

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
def test_record_keeps_foreign_redirect(root: Path, existing: str) -> None:
    redirect: Final[Path] = root / ".venv"
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))
    assert redirect.read_text(encoding="utf-8") == ".tox/dev\n"
    redirect.write_text(existing, encoding="utf-8")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert redirect.read_text(encoding="utf-8") == existing


def test_record_keeps_undecodable_redirect(root: Path) -> None:
    redirect: Final[Path] = root / ".venv"
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))
    assert redirect.read_text(encoding="utf-8") == ".tox/dev\n"
    redirect.write_bytes(b"\xff\xfe.tox/3.13\n")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert redirect.read_bytes() == b"\xff\xfe.tox/3.13\n"


def test_record_keeps_venv_directory(root: Path) -> None:
    redirect: Final[Path] = root / ".venv"
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))
    assert redirect.is_file()
    redirect.unlink()
    redirect.mkdir()

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert redirect.is_dir()


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_record_keeps_venv_symlink(root: Path) -> None:
    redirect: Final[Path] = root / ".venv"
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))
    assert redirect.is_file()
    redirect.unlink()
    redirect.symlink_to(root / ".tox" / "3.13")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert redirect.readlink() == root / ".tox" / "3.13"


def test_record_same_target_does_not_write(root: Path) -> None:
    redirect: Final[Path] = root / ".venv"
    redirect.write_text(".tox/dev", encoding="utf-8")
    os.utime(redirect, ns=(1_000_000_000, 1_000_000_000))

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))
    unchanged: Final[int] = redirect.stat().st_mtime_ns
    record_venv_redirect(root, root / ".tox" / "lint", _is_ours(root))

    assert (unchanged, redirect.read_text(encoding="utf-8")) == (1_000_000_000, ".tox/lint\n")


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
def test_record_stays_in_root_swapped_after_check(root: Path, swap_root: tuple[Callable[[], None], Path, Path]) -> None:
    swap, moved, other = swap_root
    (root / ".venv").write_text(".tox/3.13\n", encoding="utf-8")

    record_venv_redirect(root, root / ".tox" / "dev", lambda _: swap() is None)

    assert (other / ".venv").read_text(encoding="utf-8") == "../shared\n"
    assert (moved / ".venv").read_text(encoding="utf-8") == ".tox/dev\n"


@pytest.fixture
def swap_root(root: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Callable[[], None], Path, Path]:
    other: Final[Path] = tmp_path_factory.mktemp("other") / "project"
    other.mkdir()
    (other / ".venv").write_text("../shared\n", encoding="utf-8")
    moved: Final[Path] = other.with_name("moved")

    def swap() -> None:
        root.rename(moved)
        root.symlink_to(other)

    return swap, moved, other


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_record_refuses_directory_link_before_open(linked_directory: tuple[Path, Path, Path]) -> None:
    project, original, foreign = linked_directory

    record_venv_redirect(project, project / ".tox" / "lint", lambda _: True)

    assert (original.read_text(encoding="utf-8"), foreign.read_text(encoding="utf-8")) == (
        ".tox/dev\n",
        "../shared\n",
    )


@pytest.fixture(params=[pytest.param(False, id="root"), pytest.param(True, id="parent")])
def linked_directory(
    root: Path, tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest
) -> tuple[Path, Path, Path]:
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
    return project, original, foreign


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
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


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX directory-relative replacement")
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

    outcome = release_venv_redirect(root / ".venv", _is_ours(root))

    assert (outcome, (root / ".venv").exists()) == (released, not released)


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_release_stays_in_directory_swapped_after_check(
    root: Path, swap_root: tuple[Callable[[], None], Path, Path]
) -> None:
    swap, moved, other = swap_root
    (root / ".venv").write_text(".tox/lint\n", encoding="utf-8")

    assert release_venv_redirect(root / ".venv", lambda _: swap() is None)

    assert (other / ".venv").read_text(encoding="utf-8") == "../shared\n"
    assert not (moved / ".venv").exists()


def test_release_without_directory(root: Path) -> None:
    assert release_venv_redirect(root / "missing" / ".venv", _is_ours(root)) is False
