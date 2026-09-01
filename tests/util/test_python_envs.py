from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tox.util.python_envs import forget_python_env, record_python_envs

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / ".tox").mkdir()
    return tmp_path


def _catalog(root: Path) -> str:
    return (root / ".python-envs").read_text(encoding="utf-8")


def test_record_creates_catalog(root: Path) -> None:
    record_python_envs(root, root / ".tox", [root / ".tox" / "3.13", root / ".tox" / "dev"])

    assert _catalog(root) == f".tox{os.sep}3.13\n.tox{os.sep}dev\n"


def test_record_keeps_env_outside_root_absolute(root: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    outside = tmp_path_factory.mktemp("elsewhere") / "dev"

    record_python_envs(root, root / ".tox", [outside])

    assert _catalog(root) == f"{outside}\n"


def test_record_skips_dot_venv(root: Path) -> None:
    record_python_envs(root, root / ".tox", [root / ".tox" / "3.13", root / ".venv"])

    assert _catalog(root) == f".tox{os.sep}3.13\n"


def test_record_without_envs_creates_nothing(root: Path) -> None:
    record_python_envs(root, root / ".tox", [])

    assert not (root / ".python-envs").exists()


@pytest.mark.parametrize(
    "existing",
    [
        pytest.param("../shared\n", id="trailing_newline"),
        pytest.param("../shared", id="no_trailing_newline"),
        pytest.param("../shared\r\n", id="crlf"),
        pytest.param("../shared\n\n", id="blank_line"),
    ],
)
def test_record_keeps_foreign_line(root: Path, existing: str) -> None:
    (root / ".python-envs").write_text(existing, encoding="utf-8")

    record_python_envs(root, root / ".tox", [root / ".tox" / "3.13"])

    assert _catalog(root) == f".tox{os.sep}3.13\n../shared\n"


def test_record_leaves_foreign_default_last(root: Path) -> None:
    (root / ".python-envs").write_text("../first\n../default\n", encoding="utf-8")

    record_python_envs(root, root / ".tox", [root / ".tox" / "dev"])

    assert _catalog(root) == f"../first\n.tox{os.sep}dev\n../default\n"


def test_record_prunes_envs_no_longer_known(root: Path) -> None:
    record_python_envs(root, root / ".tox", [root / ".tox" / "3.12", root / ".tox" / "3.13"])

    record_python_envs(root, root / ".tox", [root / ".tox" / "3.13"])

    assert _catalog(root) == f".tox{os.sep}3.13\n"


def test_record_does_not_duplicate_hand_written_env(root: Path) -> None:
    (root / ".python-envs").write_text(f".tox{os.sep}dev\n../shared\n", encoding="utf-8")

    record_python_envs(root, root / ".tox", [root / ".tox" / "dev"])

    assert _catalog(root) == f".tox{os.sep}dev\n../shared\n"


def test_record_unchanged_does_not_write(root: Path, mocker: MockerFixture) -> None:
    record_python_envs(root, root / ".tox", [root / ".tox" / "dev"])
    write_text = mocker.spy(Path, "write_text")

    record_python_envs(root, root / ".tox", [root / ".tox" / "dev"])

    assert write_text.call_count == 0


def test_forget_drops_env(root: Path) -> None:
    record_python_envs(root, root / ".tox", [root / ".tox" / "3.13", root / ".tox" / "dev"])

    forget_python_env(root, root / ".tox", root / ".tox" / "dev")

    assert _catalog(root) == f".tox{os.sep}3.13\n"


def test_forget_leaves_other_envs(root: Path) -> None:
    record_python_envs(root, root / ".tox", [root / ".tox" / "3.13"])

    forget_python_env(root, root / ".tox", root / ".tox" / "dev")

    assert _catalog(root) == f".tox{os.sep}3.13\n"


def test_forget_without_catalog(root: Path) -> None:
    forget_python_env(root, root / ".tox", root / ".tox" / "dev")

    assert not (root / ".python-envs").exists()
