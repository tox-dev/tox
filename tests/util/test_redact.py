from __future__ import annotations

import pytest

from tox.util.redact import redact_argv, redact_value


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        pytest.param("API_TOKEN", "******", id="api-token"),
        pytest.param("PASSWORD", "******", id="password-keyword"),
        pytest.param("MY_SECRET_THING", "******", id="embedded-secret"),
        pytest.param("MY\nSECRET_THING", "******", id="newline-before-secret"),
        pytest.param("MY\r\nSECRET_THING", "******", id="crlf-before-secret"),
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
    # A command parser is needed to tell whether the next argument is this flag's value.
    assert redact_argv(["app", "--token", "hunter2"]) == ["app", "--token", "hunter2"]


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        pytest.param("--ref=it's --token=abc", "--ref=it's --token=***", id="after-flag"),
        pytest.param("it's --token=abc", "it's --token=***", id="after-positional"),
        pytest.param("-x\n--token=abc", "-x\n--token=***", id="after-line-break"),
        pytest.param("tool --token=abc | tee out", "tool --token=*************", id="script"),
        pytest.param("tool '--token=abc'", "tool '--token=****", id="quoted-script"),
        pytest.param("--tool-args=--token=abc", "--tool-args=--token=***", id="nested-flag"),
        pytest.param("--ref=main --password=a b", "--ref=main --password=***", id="mask-to-end"),
        pytest.param("badoverride;--password=hunter2", "badoverride;--password=*******", id="semicolon-delimiter"),
        pytest.param("--password=hun;ter2", "--password=********", id="semicolon-value"),
        pytest.param("--password;extra=foo", "--password;extra=***", id="semicolon-flag-name"),
    ],
)
def test_redact_argv_masks_secret_flag_inside_token(token: str, expected: str) -> None:
    assert redact_argv([token]) == [expected]


@pytest.mark.parametrize(
    "token",
    [
        pytest.param("tests/test_api.py::test[a=b]", id="test-id"),
        pytest.param("key=1", id="assignment"),
        pytest.param("--ref=token --cov=tox", id="innocuous-flags"),
        pytest.param("--url=https://u:token=abc@host", id="keyword-inside-value"),
        pytest.param("--deselect=tests/test_a.py::test[--token=1]", id="flag-inside-word"),
    ],
)
def test_redact_argv_leaves_token_without_secret_flag_alone(token: str) -> None:
    assert redact_argv([token]) == [token]


def test_redact_argv_returns_new_list() -> None:
    original = ["pytest", "--token=abc"]
    result = redact_argv(original)
    assert result is not original
    assert original == ["pytest", "--token=abc"]


def test_redact_argv_empty() -> None:
    assert redact_argv([]) == []


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        pytest.param(["app", "--prod\n-token=hunter2"], ["app", "--prod\n-token=*******"], id="newline-before-keyword"),
        pytest.param(["app", "--a\nb\nsecret=x"], ["app", "--a\nb\nsecret=*"], id="two-newlines"),
        pytest.param(["app", "--\napi-key=v"], ["app", "--\napi-key=*"], id="leading-newline"),
        pytest.param(["app", "--a\r\nb\r\nsecret=x"], ["app", "--a\r\nb\r\nsecret=*"], id="crlf"),
        pytest.param(["app", "bad;--a\nsecret=x"], ["app", "bad;--a\nsecret=*"], id="semicolon-and-newline"),
    ],
)
def test_redact_argv_masks_when_a_newline_precedes_the_keyword(argv: list[str], expected: list[str]) -> None:
    assert redact_argv(argv) == expected
