from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockFixture

    from tests.config.loader.ini.replace.conftest import ReplaceOne


@pytest.mark.parametrize("is_atty", [True, False])
def test_replace_env_set(replace_one: ReplaceOne, mocker: MockFixture, is_atty: bool) -> None:
    mocker.patch.object(sys.stdout, "isatty", return_value=is_atty)

    result = replace_one("1 {tty} 2")
    assert result == "1  2"

    result = replace_one("1 {tty:a} 2")
    assert result == f"1 {'a' if is_atty else ''} 2"

    result = replace_one("1 {tty:a:b} 2")
    assert result == f"1 {'a' if is_atty else 'b'} 2"
