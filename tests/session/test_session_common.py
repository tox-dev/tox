from __future__ import annotations

import pytest

from tox.session.env_select import CliEnv


@pytest.mark.parametrize(
    ("val", "exp"),
    [
        pytest.param(
            CliEnv(["a", "b"]),
            "CliEnv('a,b')",
            id="clienv-lparen-lbracket-quote-a-quote-comma-space-quote-b-quote-rbracket-rparen-clienv-lparen-quote-a-comma-b-quote-rparen",
        ),
        pytest.param(
            CliEnv(["ALL", "b"]),
            "CliEnv('ALL')",
            id="clienv-lparen-lbracket-quote-all-quote-comma-space-quote-b-quote-rbracket-rparen-clienv-lparen-quote-all-quote-rparen",
        ),
        pytest.param(CliEnv([]), "CliEnv()", id="clienv-lparen-lbracket-rbracket-rparen-clienv-lparen-rparen"),
        pytest.param(CliEnv(), "CliEnv()", id="clienv-lparen-rparen-clienv-lparen-rparen"),
    ],
)
def test_cli_env_repr(val: CliEnv, exp: str) -> None:
    assert repr(val) == exp


@pytest.mark.parametrize(
    ("val", "exp"),
    [
        pytest.param(
            CliEnv(["a", "b"]),
            "a,b",
            id="clienv-lparen-lbracket-quote-a-quote-comma-space-quote-b-quote-rbracket-rparen-a-comma-b",
        ),
        pytest.param(
            CliEnv(["ALL", "b"]),
            "ALL",
            id="clienv-lparen-lbracket-quote-all-quote-comma-space-quote-b-quote-rbracket-rparen-all",
        ),
        pytest.param(CliEnv([]), "<env_list>", id="clienv-lparen-lbracket-rbracket-rparen-lt-env-underscore-list-gt"),
        pytest.param(CliEnv(), "<env_list>", id="clienv-lparen-rparen-lt-env-underscore-list-gt"),
    ],
)
def test_cli_env_str(val: CliEnv, exp: str) -> None:
    assert str(val) == exp
