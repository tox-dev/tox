from __future__ import annotations

import pytest

from tox.config.loader.ini.replace import MatchExpression, find_replace_expr


@pytest.mark.parametrize(
    ("value", "exp_output"),
    [
        ("[]", [[MatchExpression([["posargs"]])]]),
        ("123[]", [["123", MatchExpression([["posargs"]])]]),
        ("[]123", [[MatchExpression([["posargs"]]), "123"]]),
        (r"\[\] []", [["[] ", MatchExpression([["posargs"]])]]),
        (r"[\] []", [["[] ", MatchExpression([["posargs"]])]]),
        (r"\[] []", [["[] ", MatchExpression([["posargs"]])]]),
        ("{foo}", [[MatchExpression([["foo"]])]]),
        (r"\{foo} {bar}", [["{foo} ", MatchExpression([["bar"]])]]),
        ("{foo} {bar}", [[MatchExpression([["foo"]]), " ", MatchExpression([["bar"]])]]),
        (r"{foo\} {bar}", [["{foo} ", MatchExpression([["bar"]])]]),
        (r"{foo:{bar}}", [[MatchExpression([["foo"], [MatchExpression([["bar"]])]])]]),
        (r"{\{}", [[MatchExpression([["{"]])]]),
        (r"{\}}", [[MatchExpression([["}"]])]]),
    ],
)
def test_match(value: str, exp_output: list[str | MatchExpression]) -> None:
    assert find_replace_expr(value) == (exp_output, len(value))
