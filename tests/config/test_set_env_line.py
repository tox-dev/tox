from __future__ import annotations

import pytest

from tox.config.set_env_line import format_line, split_line


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        pytest.param(
            r'WINPATH="C:\tools;C:\bin\\"',
            ("WINPATH", r'"C:\tools;C:\bin\\"', ""),
            id="quoted-value-ending-with-backslash",
        ),
        pytest.param(
            r'WINPATH="C:\tools;C:\bin\\"; sys_platform == "win32"',
            ("WINPATH", r'"C:\tools;C:\bin\\"', 'sys_platform == "win32"'),
            id="quoted-value-ending-with-backslash-and-marker",
        ),
        pytest.param(r'MSG="say \"hi;\""', ("MSG", r'"say \"hi;\""', ""), id="escaped-quote-stays-quoted"),
        pytest.param('MSG="it\'s; fine"', ("MSG", '"it\'s; fine"', ""), id="other-quote-stays-quoted"),
        pytest.param(r"WINPATH=C:\tools\\;C:\bin", ("WINPATH", r"C:\tools\;C:\bin", ""), id="backslash-before-escape"),
    ],
)
def test_split_line(line: str, expected: tuple[str, str, str]) -> None:
    assert split_line(line) == expected


def test_format_line_round_trips_backslash_before_semicolon() -> None:
    line = format_line("WINPATH", r"C:\tools\;C:\bin", "sys_platform == 'win32'")
    assert split_line(line) == ("WINPATH", r"C:\tools\;C:\bin", "sys_platform == 'win32'")


def test_format_line_round_trips_value_ending_with_backslash() -> None:
    line = format_line("WINPATH", "C:\\tools\\", "sys_platform == 'win32'")
    assert split_line(line) == ("WINPATH", "C:\\tools\\", "sys_platform == 'win32'")
