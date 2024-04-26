from __future__ import annotations

from tox.config.types import Command, EnvList


def tests_command_repr() -> None:
    cmd = Command(["python", "-m", "pip", "list"])
    assert repr(cmd) == "Command(args=['python', '-m', 'pip', 'list'])"
    assert cmd.invert_exit_code is False
    assert cmd.ignore_exit_code is False


def tests_command_repr_ignore() -> None:
    cmd = Command(["-", "python", "-m", "pip", "list"])
    assert repr(cmd) == "Command(args=['-', 'python', '-m', 'pip', 'list'])"
    assert cmd.invert_exit_code is False
    assert cmd.ignore_exit_code is True


def tests_command_repr_invert() -> None:
    cmd = Command(["!", "python", "-m", "pip", "list"])
    assert repr(cmd) == "Command(args=['!', 'python', '-m', 'pip', 'list'])"
    assert cmd.invert_exit_code is True
    assert cmd.ignore_exit_code is False


def tests_command_eq() -> None:
    cmd_1 = Command(["python", "-m", "pip", "list"])
    cmd_2 = Command(["python", "-m", "pip", "list"])
    assert cmd_1 == cmd_2


def tests_command_ne() -> None:
    cmd_1 = Command(["python", "-m", "pip", "list"])
    cmd_2 = Command(["-", "python", "-m", "pip", "list"])
    cmd_3 = Command(["!", "python", "-m", "pip", "list"])
    assert cmd_1 != cmd_2 != cmd_3


def tests_env_list_repr() -> None:
    env = EnvList(["py39", "py38"])
    assert repr(env) == "EnvList(['py39', 'py38'])"


def tests_env_list_eq() -> None:
    env_1 = EnvList(["py39", "py38"])
    env_2 = EnvList(["py39", "py38"])
    assert env_1 == env_2


def tests_env_list_ne() -> None:
    env_1 = EnvList(["py39", "py38"])
    env_2 = EnvList(["py38", "py39"])
    assert env_1 != env_2
