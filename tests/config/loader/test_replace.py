from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.config.loader.replacer import MatchExpression, find_replace_expr
from tox.report import HandledError

if TYPE_CHECKING:
    from .conftest import ReplaceOne


@pytest.mark.parametrize(
    ("value", "exp_output"),
    [
        pytest.param(
            "[]",
            [MatchExpression([["posargs"]])],
            id="lbracket-rbracket-matchexpression-lparen-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            "123[]",
            ["123", MatchExpression([["posargs"]])],
            id="123-lbracket-rbracket-123-matchexpression-lparen-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            "[]123",
            [MatchExpression([["posargs"]]), "123"],
            id="lbracket-rbracket-123-matchexpression-lparen-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-rparen-123",
        ),
        pytest.param(
            r"\[\] []",
            ["[] ", MatchExpression([["posargs"]])],
            id="backslash-lbracket-backslash-rbracket-space-lbracket-rbracket-lbracket-rbracket-space-matchexpression-lparen-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            r"[\] []",
            ["[] ", MatchExpression([["posargs"]])],
            id="lbracket-backslash-rbracket-space-lbracket-rbracket-lbracket-rbracket-space-matchexpression-lparen-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            r"\[] []",
            ["[] ", MatchExpression([["posargs"]])],
            id="backslash-lbracket-rbracket-space-lbracket-rbracket-lbracket-rbracket-space-matchexpression-lparen-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            "{foo}",
            [MatchExpression([["foo"]])],
            id="open-foo-close-matchexpression-lparen-lbracket-lbracket-quote-foo-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            r"\{foo} {bar}",
            ["{foo} ", MatchExpression([["bar"]])],
            id="backslash-open-foo-close-space-open-bar-close-open-foo-close-space-matchexpression-lparen-lbracket-lbracket-quote-bar-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            "{foo} {bar}",
            [MatchExpression([["foo"]]), " ", MatchExpression([["bar"]])],
            id="open-foo-close-space-open-bar-close-matchexpression-lparen-lbracket-lbracket-quote-foo-quote-rbracket-rbracket-rparen-space-matchexpression-lparen-lbracket-lbracket-quote-bar-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            r"{foo\} {bar}",
            ["{foo} ", MatchExpression([["bar"]])],
            id="open-foo-backslash-close-space-open-bar-close-open-foo-close-space-matchexpression-lparen-lbracket-lbracket-quote-bar-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            r"{foo:{bar}}",
            [MatchExpression([["foo"], [MatchExpression([["bar"]])]])],
            id="open-foo-colon-open-bar-close-close-matchexpression-lparen-lbracket-lbracket-quote-foo-quote-rbracket-comma-space-lbracket-matchexpression-lparen-lbracket-lbracket-quote-bar-quote-rbracket-rbracket-rparen-rbracket-rbracket-rparen",
        ),
        pytest.param(
            r"{foo\::{bar}}",
            [MatchExpression([["foo:"], [MatchExpression([["bar"]])]])],
            id="open-foo-backslash-colon-colon-open-bar-close-close-matchexpression-lparen-lbracket-lbracket-quote-foo-colon-quote-rbracket-comma-space-lbracket-matchexpression-lparen-lbracket-lbracket-quote-bar-quote-rbracket-rbracket-rparen-rbracket-rbracket-rparen",
        ),
        pytest.param(
            r"{foo:B:c:D:e}",
            [MatchExpression([["foo"], ["B"], ["c"], ["D"], ["e"]])],
            id="open-foo-colon-b-colon-c-colon-d-colon-e-close-matchexpression-lparen-lbracket-lbracket-quote-foo-quote-rbracket-comma-space-lbracket-quote-b-quote-rbracket-comma-space-lbracket-quote-c-quote-rbracket-comma-space-lbracket-quote-d-quote-rbracket-comma-space-lbracket-quote-e-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            r"{\{}",
            [MatchExpression([["{"]])],
            id="open-backslash-open-close-matchexpression-lparen-lbracket-lbracket-quote-open-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
            r"{\}}",
            [MatchExpression([["}"]])],
            id="open-backslash-close-close-matchexpression-lparen-lbracket-lbracket-quote-close-quote-rbracket-rbracket-rparen",
        ),
        pytest.param(
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
            id="p-open-foo-colon-b-open-a-open-r-close-colon-t-close-colon-open-ba-close-z-close-s-p-matchexpression-lparen-lbracket-lbracket-quote-foo-quote-rbracket-comma-space-lbracket-quote-b-quote-comma-space-matchexpression-lparen-lbracket-lbracket-quote-a-quote-comma-space-matchexpression-lparen-lbracket-lbracket-quote-r-quote-rbracket-rbracket-rparen-rbracket-comma-space-lbracket-quote-t-quote-rbracket-rbracket-rparen-rbracket-comma-space-lbracket-matchexpression-lparen-lbracket-lbracket-quote-ba-quote-rbracket-rbracket-rparen-comma-space-quote-z-quote-rbracket-rbracket-rparen-s",
        ),
        pytest.param("\\", ["\\"], id="backslash-backslash"),
        pytest.param(r"\d", ["\\d"], id="backslash-d-backslash-d"),
        pytest.param(
            r"C:\WINDOWS\foo\bar",
            [r"C:\WINDOWS\foo\bar"],
            id="c-colon-backslash-windows-backslash-foo-backslash-bar-c-colon-backslash-windows-backslash-foo-backslash-bar",
        ),
    ],
)
def test_match_expr(value: str, exp_output: list[str | MatchExpression]) -> None:
    assert find_replace_expr(value) == exp_output


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("py-{foo,bar}", id="py-dash-open-foo-comma-bar-close-none"),
        pytest.param("py37-{base,i18n},b", id="py37-dash-open-base-comma-i18n-close-comma-b-none"),
        pytest.param("py37-{i18n,base},b", id="py37-dash-open-i18n-comma-base-close-comma-b-none"),
        pytest.param("{toxinidir,}", id="open-toxinidir-comma-close-none"),
    ],
)
def test_dont_replace(replace_one: ReplaceOne, value: str) -> None:
    assert replace_one(value) == value


@pytest.mark.parametrize(
    ("value", "exp_exception"),
    [
        pytest.param(
            "{env}",
            r"MatchError\('No variable name was supplied in {env} substitution'\)",
            id="open-env-close-matcherror-backslash-lparen-quote-no-space-variable-space-name-space-was-space-supplied-space-in-space-open-env-close-space-substitution-quote-backslash-rparen",
        ),
        pytest.param(
            "{factor}",
            r"MatchError\('No label was supplied in {factor} substitution'\)",
            id="open-factor-close-matcherror-backslash-lparen-quote-no-space-label-space-was-space-supplied-space-in-space-open-factor-close-space-substitution-quote-backslash-rparen",
        ),
    ],
)
def test_dont_replace_raises(replace_one: ReplaceOne, value: str, exp_exception: str) -> None:
    with pytest.raises(HandledError, match=exp_exception):
        replace_one(value)


def test_replace_factor_ini_uses_fallback(replace_one: ReplaceOne) -> None:
    assert replace_one("{factor:label:fallback}") == "fallback"


@pytest.mark.parametrize(
    ("match_expression", "exp_repr"),
    [
        pytest.param(
            MatchExpression([["posargs"]]),
            "MatchExpression(expr=[['posargs']], term_pos=None)",
            id="matchexpression-lparen-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-rparen-matchexpression-lparen-expr-equal-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-comma-space-term-underscore-pos-equal-none-rparen",
        ),
        pytest.param(
            MatchExpression([["posargs"]], 1),
            "MatchExpression(expr=[['posargs']], term_pos=1)",
            id="matchexpression-lparen-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-comma-space-1-rparen-matchexpression-lparen-expr-equal-lbracket-lbracket-quote-posargs-quote-rbracket-rbracket-comma-space-term-underscore-pos-equal-1-rparen",
        ),
        pytest.param(
            MatchExpression("foo", -42),
            "MatchExpression(expr='foo', term_pos=-42)",
            id="matchexpression-lparen-quote-foo-quote-comma-space-dash-42-rparen-matchexpression-lparen-expr-equal-quote-foo-quote-comma-space-term-underscore-pos-equal-dash-42-rparen",
        ),
    ],
)
def test_match_expression_repr(match_expression: MatchExpression, exp_repr: str) -> None:
    print(match_expression)  # ruff:ignore[print]  # test output
    assert repr(match_expression) == exp_repr
