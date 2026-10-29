from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from tox.execute.util import shebang

if TYPE_CHECKING:
    from pathlib import Path


def test_shebang_found(tmp_path: Path) -> None:
    script_path = tmp_path / "a"
    script_path.write_text("#!  /bin/python \t-c\t")
    assert shebang(str(script_path)) == ["/bin/python", "-c"]


def test_shebang_quoted_interpreter_path(tmp_path: Path) -> None:
    script_path = tmp_path / "a"
    script_path.write_text('#! "/Program Files/Python/python.exe" -c\n', encoding="utf-8")
    assert shebang(str(script_path)) == ["/Program Files/Python/python.exe", "-c"]


@pytest.mark.parametrize(
    "interpreter",
    [
        pytest.param("/rock'n'roll/bin/python", id="single_quotes"),
        pytest.param('/a"b"/bin/python', id="double_quotes"),
        pytest.param("/it's/bin/python", id="unpaired_quote"),
        pytest.param('"/bin/python', id="unclosed_leading_quote"),
        pytest.param("/c\\d/bin/python", id="backslash"),
        pytest.param("/e\u00a0f/bin/python", id="no_break_space"),
    ],
)
def test_shebang_interpreter_is_literal(tmp_path: Path, interpreter: str) -> None:
    script_path: Final[Path] = tmp_path / "a"
    script_path.write_text(f"#!{interpreter} -c\n", encoding="utf-8")
    assert shebang(str(script_path)) == [interpreter, "-c"]


def test_shebang_arguments_keep_shell_splitting(tmp_path: Path) -> None:
    script_path: Final[Path] = tmp_path / "a"
    script_path.write_text("#!/usr/bin/env -S 'A=b' \\c\n", encoding="utf-8")
    assert shebang(str(script_path)) == ["/usr/bin/env", "-S", "A=b", "c"]


def test_shebang_unclosed_argument_quote(tmp_path: Path) -> None:
    script_path: Final[Path] = tmp_path / "a"
    script_path.write_text("#!/usr/bin/env -S 'unclosed\n", encoding="utf-8")
    assert shebang(str(script_path)) is None


def test_shebang_empty(tmp_path: Path) -> None:
    script_path: Final[Path] = tmp_path / "a"
    script_path.write_text("#! \n", encoding="utf-8")
    assert shebang(str(script_path)) is None


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
