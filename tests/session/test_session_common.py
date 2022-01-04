from __future__ import annotations

import pytest

from tox.session.env_select import CliEnv


@pytest.mark.parametrize(
    ("val", "exp"),
    [
        (CliEnv(["a", "b"]), "CliEnv('a,b')"),
        (CliEnv(["ALL", "b"]), "CliEnv('ALL')"),
        (CliEnv([]), "CliEnv()"),
        (CliEnv(), "CliEnv()"),
    ],
)
def test_cli_env_repr(val: CliEnv, exp: str) -> None:
    assert repr(val) == exp


@pytest.mark.parametrize(
    ("val", "exp"),
    [
        (CliEnv(["a", "b"]), "a,b"),
        (CliEnv(["ALL", "b"]), "ALL"),
        (CliEnv([]), "<env_list>"),
        (CliEnv(), "<env_list>"),
    ],
)
def test_cli_env_str(val: CliEnv, exp: str) -> None:
    assert str(val) == exp
