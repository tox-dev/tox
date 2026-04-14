from __future__ import annotations

import pytest

from tox.util.redact import redact_argv, redact_value


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        pytest.param("API_TOKEN", "******", id="api-token"),
        pytest.param("PASSWORD", "******", id="password-keyword"),
        pytest.param("MY_SECRET_THING", "******", id="embedded-secret"),
        pytest.param("FOO", "secret", id="non-matching"),
        pytest.param("PATH", "secret", id="path"),
    ],
)
def test_redact_value_matches_secret_keywords(name: str, expected: str) -> None:
    assert redact_value(name, "secret") == expected


def test_redact_value_preserves_length() -> None:
    assert redact_value("API_KEY", "abcde") == "*****"


def test_redact_argv_masks_inline_value_for_secret_flag() -> None:
    result = redact_argv(["pytest", "--token=hunter2", "tests"])
    assert result == ["pytest", "--token=*******", "tests"]


def test_redact_argv_masks_short_flag() -> None:
    result = redact_argv(["foo", "-key=abc"])
    assert result == ["foo", "-key=***"]


def test_redact_argv_leaves_innocuous_flags_alone() -> None:
    result = redact_argv(["pytest", "-k", "test_foo", "--cov=tox"])
    assert result == ["pytest", "-k", "test_foo", "--cov=tox"]


def test_redact_argv_does_not_mask_space_separated_value() -> None:
    # we deliberately do NOT redact `--token hunter2` because we cannot reliably tell where a flag value ends without
    # parser-specific knowledge; this asserts the documented limitation.
    result = redact_argv(["app", "--token", "hunter2"])
    assert result == ["app", "--token", "hunter2"]


def test_redact_argv_returns_new_list() -> None:
    original = ["pytest", "--token=abc"]
    result = redact_argv(original)
    assert result is not original
    assert original == ["pytest", "--token=abc"]


def test_redact_argv_empty() -> None:
    assert redact_argv([]) == []
