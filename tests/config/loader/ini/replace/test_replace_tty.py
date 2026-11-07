from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockFixture

    from tests.config.loader.conftest import ReplaceOne


@pytest.mark.parametrize(
    ("template", "is_atty", "expected"),
    [
        pytest.param("1 {tty} 2", True, "1  2", id="plain-atty"),
        pytest.param("1 {tty} 2", False, "1  2", id="plain-no-atty"),
        pytest.param("1 {tty:a} 2", True, "1 a 2", id="one-arg-atty"),
        pytest.param("1 {tty:a} 2", False, "1  2", id="one-arg-no-atty"),
        pytest.param("1 {tty:a:b} 2", True, "1 a 2", id="two-args-atty"),
        pytest.param("1 {tty:a:b} 2", False, "1 b 2", id="two-args-no-atty"),
    ],
)
def test_replace_env_set(
    replace_one: ReplaceOne, mocker: MockFixture, template: str, is_atty: bool, expected: str
) -> None:
    mocker.patch.object(sys.stdout, "isatty", return_value=is_atty)
    assert replace_one(template) == expected
