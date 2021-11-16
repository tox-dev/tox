from __future__ import annotations

import pytest

from tox.config.loader.ini.replace import find_replace_part


@pytest.mark.parametrize(
    ("value", "result"),
    [
        ("[]", (0, 1, "posargs")),
        ("123[]", (3, 4, "posargs")),
        ("[]123", (0, 1, "posargs")),
        (r"\[\] []", (5, 6, "posargs")),
        (r"[\] []", (4, 5, "posargs")),
        (r"\[] []", (4, 5, "posargs")),
        ("{foo}", (0, 4, "foo")),
        (r"\{foo} {bar}", (7, 11, "bar")),
        ("{foo} {bar}", (0, 4, "foo")),
        (r"{foo\} {bar}", (7, 11, "bar")),
        (r"{foo:{bar}}", (5, 9, "bar")),
        (r"{\{}", (0, 3, r"\{")),
        (r"{\}}", (0, 3, r"\}")),
    ],
)
def test_match(value: str, result: tuple[int, int, str]) -> None:
    assert find_replace_part(value, 0) == result
