from __future__ import annotations

from typing import TYPE_CHECKING

from tox.execute.util import shebang

if TYPE_CHECKING:
    from pathlib import Path


def test_shebang_found(tmp_path: Path) -> None:
    script_path = tmp_path / "a"
    script_path.write_text("#!  /bin/python \t-c\t")
    assert shebang(str(script_path)) == ["/bin/python", "-c"]


def test_shebang_file_missing(tmp_path: Path) -> None:
    script_path = tmp_path / "a"
    assert shebang(str(script_path)) is None


def test_shebang_no_shebang(tmp_path: Path) -> None:
    script_path = tmp_path / "a"
    script_path.write_bytes(b"magic")
    assert shebang(str(script_path)) is None


def test_shebang_non_utf8_file(tmp_path: Path) -> None:
    script_path, content = tmp_path / "a", b"#!" + bytearray.fromhex("c0")
    script_path.write_bytes(content)
    assert shebang(str(script_path)) is None
