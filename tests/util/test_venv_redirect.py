from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tox.util.venv_redirect import forget_venv_redirect, record_venv_redirect, release_venv_redirect

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytest_mock import MockerFixture


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / ".tox").mkdir()
    return tmp_path


def _is_ours(root: Path) -> Callable[[Path], bool]:
    return lambda path: path.is_relative_to(root / ".tox")


def test_record_creates_redirect(root: Path) -> None:
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (root / ".venv").read_text(encoding="utf-8") == ".tox/dev\n"


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
    (root / ".venv").write_text(existing, encoding="utf-8")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (root / ".venv").read_text(encoding="utf-8") == existing


def test_record_keeps_undecodable_redirect(root: Path) -> None:
    (root / ".venv").write_bytes(b"\xff\xfe.tox/3.13\n")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (root / ".venv").read_bytes() == b"\xff\xfe.tox/3.13\n"


def test_record_keeps_venv_directory(root: Path) -> None:
    (root / ".venv").mkdir()

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (root / ".venv").is_dir()


@pytest.mark.skipif(sys.platform == "win32", reason="creating symlinks needs privileges on Windows")
def test_record_keeps_venv_symlink(root: Path) -> None:
    (root / ".venv").symlink_to(root / ".tox" / "3.13")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert (root / ".venv").readlink() == root / ".tox" / "3.13"


def test_record_same_target_does_not_write(root: Path, mocker: MockerFixture) -> None:
    (root / ".venv").write_text(".tox/dev", encoding="utf-8")
    write_text = mocker.spy(Path, "write_text")

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert write_text.call_count == 0


def test_record_warns_when_write_fails(root: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture) -> None:
    mocker.patch.object(Path, "write_text", side_effect=PermissionError("read-only"))

    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    assert "could not point" in caplog.text


def test_forget_removes_redirect_to_env(root: Path) -> None:
    record_venv_redirect(root, root / ".tox" / "dev", _is_ours(root))

    forget_venv_redirect(root, root / ".tox" / "dev")

    assert not (root / ".venv").exists()


def test_forget_keeps_redirect_to_other_env(root: Path) -> None:
    record_venv_redirect(root, root / ".tox" / "3.13", _is_ours(root))

    forget_venv_redirect(root, root / ".tox" / "dev")

    assert (root / ".venv").read_text(encoding="utf-8") == ".tox/3.13\n"


def test_forget_without_redirect(root: Path) -> None:
    forget_venv_redirect(root, root / ".tox" / "dev")

    assert not (root / ".venv").exists()


@pytest.mark.parametrize(
    ("target", "released"),
    [pytest.param(".tox/lint", True, id="ours"), pytest.param("../shared", False, id="foreign")],
)
def test_release_redirect_only_when_ours(root: Path, target: str, released: bool) -> None:
    (root / ".venv").write_text(f"{target}\n", encoding="utf-8")

    outcome = release_venv_redirect(root / ".venv", _is_ours(root))

    assert (outcome, (root / ".venv").exists()) == (released, not released)
