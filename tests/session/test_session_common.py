import pytest

from tox.session.common import CliEnv


@pytest.mark.parametrize(
    "val, exp",
    [
        (CliEnv(["a", "b"]), "CliEnv(['a', 'b'])"),
        (CliEnv(["ALL", "b"]), "CliEnv()"),
        (CliEnv([]), "CliEnv([])"),
    ],
)
def test_cli_env_repr(val: CliEnv, exp: str) -> None:
    assert repr(val) == exp


def test_cli_env_repr_all() -> None:
    env = CliEnv(["ALL", "b"])
    assert repr(env) == "CliEnv()"


@pytest.mark.parametrize(
    "val, exp",
    [
        (CliEnv(["a", "b"]), "a,b"),
        (CliEnv(["ALL", "b"]), "ALL"),
        (CliEnv([]), ""),
    ],
)
def test_cli_env_str(val: CliEnv, exp: str) -> None:
    assert str(val) == exp
