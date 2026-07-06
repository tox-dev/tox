from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tox.util.file_view import create_session_view

if TYPE_CHECKING:
    from tox.pytest import MonkeyPatch


def test_create_session_view_copies(tmp_path: Path) -> None:
    package = tmp_path / "pkg.whl"
    package.write_bytes(b"data")
    result = create_session_view(package, tmp_path / "temp")
    assert result.read_bytes() == b"data"
    assert result.parent.parent == tmp_path / "temp"


def test_create_session_view_no_common_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    """A source without a common path with the session dir (e.g. cross-drive) must not crash the copy."""
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "pkg.whl").write_bytes(b"data")
    monkeypatch.chdir(tmp_path)

    result = create_session_view(Path("dist/pkg.whl"), tmp_path / "temp")

    assert result.is_absolute()
    assert result.read_bytes() == b"data"
