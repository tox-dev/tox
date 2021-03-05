from typing import Tuple

import pytest

from tox.config.loader.ini.replace import new_find_replace_part as find_replace_part


@pytest.mark.parametrize(
    ("value", "result"),
    [
        ("[]", (0, 1, "posargs")),
        ("123[]", (3, 4, "posargs")),
        ("[]123", (0, 1, "posargs")),
    ],
)
def test_match(value: str, result: Tuple[int, int, str]) -> None:
    assert find_replace_part(value, 0) == result
