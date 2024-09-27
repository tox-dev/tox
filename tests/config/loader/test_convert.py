from __future__ import annotations

from typing import Any, Iterable

import pytest

from tox.config.loader.convert import ConditionalSetting, ConditionalValue


@pytest.mark.parametrize(
    ("condition", "env_name", "result"),
    [
        (None, "a", True),
        (None, "a-b", True),
        ("a", "a", True),
        ("!a", "a", False),
        ("a", "b", False),
        ("!a", "b", True),
        ("a", "a-b", True),
        ("!a", "a-b", False),
        # or
        ("a,b", "a", True),
        ("a,b", "b", True),
        ("a,b", "c", False),
        ("a,b", "a-b", True),
        ("!a,!b", "c", True),
        # and
        ("a-b", "a", False),
        ("a-b", "c", False),
        ("a-b", "a-b", True),
        ("a-!b", "a-b", False),
        ("!a-b", "a-b", False),
    ],
)
def test_conditional_value_matches(condition: str, env_name: str, result: bool) -> None:
    assert ConditionalValue(42, condition).matches(env_name) is result


@pytest.mark.parametrize(
    ("values", "env_name", "result"),
    [
        ([], "a", []),
        ([ConditionalValue(42, None)], "a", [42]),
        ([ConditionalValue(42, None)], "b", [42]),
        ([ConditionalValue(42, "!a")], "a", []),
        ([ConditionalValue(42, "!a")], "b", [42]),
        ([ConditionalValue(42, "a"), ConditionalValue(43, "!a")], "a", [42]),
        ([ConditionalValue(42, "a"), ConditionalValue(43, "!a")], "b", [43]),
        ([ConditionalValue(42, "a"), ConditionalValue(43, "a")], "a", [42, 43]),
    ],
)
def test_conditional_setting_filter(values: Iterable[ConditionalValue], env_name: str, result: list[Any]) -> None:
    setting = ConditionalSetting(values)
    assert list(setting.filter(env_name)) == result
