from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from tox.execute.util import batch_file_command_line, is_batch_file, shebang
from tox.tox_env.errors import Fail

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


@pytest.mark.parametrize(
    ("exe", "expected"),
    [
        pytest.param(r"C:\a\npm.cmd", True, id="cmd"),
        pytest.param(r"C:\a\make.bat", True, id="bat"),
        pytest.param(r"C:\a\NPM.CMD", True, id="upper_case"),
        pytest.param(r"C:\a\npm.cmd. .", True, id="trailing_dots_and_spaces"),
        pytest.param(r"C:\a\python.exe", False, id="exe"),
        pytest.param(r"C:\a.cmd\python", False, id="folder"),
        pytest.param("cmd", False, id="no_extension"),
    ],
)
def test_is_batch_file(exe: str, expected: bool) -> None:
    assert is_batch_file(exe) is expected


@pytest.mark.parametrize(
    ("arg", "expected"),
    [
        pytest.param("v1.0", "v1.0", id="plain"),
        pytest.param(r"C:\a\b_c", r"C:\a\b_c", id="path"),
        pytest.param("", '""', id="empty"),
        pytest.param("a b", '"a b"', id="space"),
        pytest.param("v1.0&next", '"v1.0&next"', id="ampersand"),
        pytest.param("a|b<c>d^e(f)!g!", '"a|b<c>d^e(f)!g!"', id="operators"),
        pytest.param("--a=b,c;d", '"--a=b,c;d"', id="argument_delimiters"),
        pytest.param('a b" & next & "', '"a b"" & next & """', id="quote"),
        pytest.param('a\\"&b', '"a\\\\""&b"', id="backslash_quote"),
        pytest.param("a\\", '"a\\\\"', id="trailing_backslash"),
        pytest.param("%PATH%", '"%%cd:~,%PATH%%cd:~,%"', id="variable"),
    ],
)
def test_batch_file_command_line(arg: str, expected: str) -> None:
    result: Final[str] = batch_file_command_line(r"C:\a b\c.cmd", [arg, "end"])
    assert result == rf'cmd.exe /e:ON /v:OFF /d /c ""C:\a b\c.cmd" {expected} end"'


def test_batch_file_command_line_script_only() -> None:
    assert batch_file_command_line(r"C:\%a%\c.cmd", []) == r'cmd.exe /e:ON /v:OFF /d /c ""C:\%%cd:~,%a%%cd:~,%\c.cmd""'


@pytest.mark.parametrize("char", ["\r", "\n", "\0"])
def test_batch_file_command_line_arg_cannot_be_quoted(char: str) -> None:
    with pytest.raises(Fail, match=r"cannot pass an argument containing a line break or null character to .*c\.cmd"):
        batch_file_command_line(r"C:\c.cmd", ["a", f"part{char}next"])


@pytest.mark.parametrize("char", ['"', "\r", "\n", "\0"])
def test_batch_file_command_line_script_cannot_be_quoted(char: str) -> None:
    with pytest.raises(Fail, match=r"cannot run batch file .*, its name cannot be quoted"):
        batch_file_command_line(f"a{char}&next&.cmd", [])
