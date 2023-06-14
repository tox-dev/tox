from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.config.loader.ini.replace import MatchExpression, find_replace_expr
from tox.report import HandledError

if TYPE_CHECKING:
    from tests.config.loader.ini.replace.conftest import ReplaceOne


@pytest.mark.parametrize(
    ("value", "exp_output"),
    [
        ("[]", [MatchExpression([["posargs"]])]),
        ("123[]", ["123", MatchExpression([["posargs"]])]),
        ("[]123", [MatchExpression([["posargs"]]), "123"]),
        (r"\[\] []", ["[] ", MatchExpression([["posargs"]])]),
        (r"[\] []", ["[] ", MatchExpression([["posargs"]])]),
        (r"\[] []", ["[] ", MatchExpression([["posargs"]])]),
        ("{foo}", [MatchExpression([["foo"]])]),
        (r"\{foo} {bar}", ["{foo} ", MatchExpression([["bar"]])]),
        ("{foo} {bar}", [MatchExpression([["foo"]]), " ", MatchExpression([["bar"]])]),
        (r"{foo\} {bar}", ["{foo} ", MatchExpression([["bar"]])]),
        (r"{foo:{bar}}", [MatchExpression([["foo"], [MatchExpression([["bar"]])]])]),
        (r"{foo\::{bar}}", [MatchExpression([["foo:"], [MatchExpression([["bar"]])]])]),
        (r"{foo:B:c:D:e}", [MatchExpression([["foo"], ["B"], ["c"], ["D"], ["e"]])]),
        (r"{\{}", [MatchExpression([["{"]])]),
        (r"{\}}", [MatchExpression([["}"]])]),
        (
            r"p{foo:b{a{r}:t}:{ba}z}s",
            [
                "p",
                MatchExpression(
                    [
                        ["foo"],
                        [
                            "b",
                            MatchExpression(
                                [
                                    ["a", MatchExpression([["r"]])],
                                    ["t"],
                                ],
                            ),
                        ],
                        [
                            MatchExpression(
                                [["ba"]],
                            ),
                            "z",
                        ],
                    ],
                ),
                "s",
            ],
        ),
        ("\\", ["\\"]),
        (r"\d", ["\\d"]),
        (r"C:\WINDOWS\foo\bar", [r"C:\WINDOWS\foo\bar"]),
    ],
)
def test_match_expr(value: str, exp_output: list[str | MatchExpression]) -> None:
    assert find_replace_expr(value) == exp_output


@pytest.mark.parametrize(
    ("value", "exp_exception"),
    [
        ("py-{foo,bar}", None),
        ("py37-{base,i18n},b", None),
        ("py37-{i18n,base},b", None),
        ("{toxinidir,}", None),
        ("{env}", r"MatchError\('No variable name was supplied in {env} substitution'\)"),
    ],
)
def test_dont_replace(replace_one: ReplaceOne, value: str, exp_exception: str | None) -> None:
    """Test that invalid expressions are not replaced."""
    if exp_exception:
        with pytest.raises(HandledError, match=exp_exception):
            replace_one(value)
    else:
        assert replace_one(value) == value


@pytest.mark.parametrize(
    ("match_expression", "exp_repr"),
    [
        (MatchExpression([["posargs"]]), "MatchExpression(expr=[['posargs']], term_pos=None)"),
        (MatchExpression([["posargs"]], 1), "MatchExpression(expr=[['posargs']], term_pos=1)"),
        (MatchExpression("foo", -42), "MatchExpression(expr='foo', term_pos=-42)"),
    ],
)
def test_match_expression_repr(match_expression: MatchExpression, exp_repr: str) -> None:
    print(match_expression)  # noqa: T201
    assert repr(match_expression) == exp_repr
