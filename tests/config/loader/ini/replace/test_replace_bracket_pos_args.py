from pathlib import Path
from typing import Any, List, Optional

import pytest

from tox.config.main import Config
from tox.config.set_env import SetEnv
from tox.config.source.tox_ini import ToxIni
from tox.config.types import Command
from tox.tox_env.python.virtual_env.runner import VirtualEnvRunner

# ConfigError = tox.exception.ConfigError
ConfigError = TypeError


@pytest.fixture()
def get_option(tmp_path: Path) -> Any:
    def do(tox_ini: str, option_name: str, pos_args: Optional[List[str]] = None) -> Any:
        if not pos_args:
            pos_args = []
        tox_ini_file = tmp_path / "tox.ini"
        tox_ini_file.write_text(tox_ini)
        ini = ToxIni(tox_ini_file)
        config = Config(ini, overrides=[], root=tmp_path, pos_args=pos_args, work_dir=tmp_path)
        options: Any = None
        journal: Any = None
        log_handler: Any = None
        env = VirtualEnvRunner(config.get_env("python"), config.core, options, journal, log_handler)
        value = env.conf[option_name]
        if isinstance(value, Command):
            return value.args
        if isinstance(value, SetEnv):
            return value._raw
        return value

    return do


def test_get_path(get_option: Any) -> None:
    """[] is not substituted in options of type path"""
    value = get_option(
        """
        [testenv]
        changedir = []
        """,
        "changedir",
    )
    assert str(value)[-2:] == "[]"


def test_get_list(get_option: Any) -> None:
    """[] is not substituted in options of type list"""
    value = get_option(
        """
        [testenv]
        extras = []
        """,
        "extras",
    )
    assert list(value) == ["[]"]


def test_dict_setenv(get_option: Any) -> None:
    """[] is not substituted in options of type dict_setenv"""
    value = get_option(
        """
        [testenv]
        setenv =
          FOO = []
        """,
        "setenv",
    )
    assert value["FOO"] == "[]"


@pytest.mark.xfail(raises=KeyError, reason="interrupt_timeout is not implemented in tox4")  # noqa: SC200
def test_get_float(get_option: Any) -> None:
    """[] is not substituted in options of type float"""
    with pytest.raises(ConfigError):
        get_option(
            """
            [testenv]
            interrupt_timeout = []
            """,
            "interrupt_timeout",
        )


def test_get_bool(get_option: Any) -> None:
    """[] is not substituted in options of type bool"""
    with pytest.raises(ConfigError):
        get_option(
            """
            [testenv]
            skip_install = []
            """,
            "skip_install",
        )


@pytest.mark.xfail(raises=AssertionError)  # noqa: SC200
def test_get_argv_list(get_option: Any) -> None:
    """[] is substituted in options of type argvlist"""
    value = get_option(
        """
        [testenv]
        commands = foo []
        """,
        "commands",
    )
    assert value == [["foo"]]


@pytest.mark.xfail(raises=AssertionError)  # noqa: SC200
def test_get_argv_list_nonempty(get_option: Any) -> None:
    """[] is substituted in options of type argvlist"""
    value = get_option(
        """
        [testenv]
        commands = foo []
        """,
        "commands",
        ["bar"],
    )
    assert value == [["foo", "bar"]]


@pytest.mark.xfail(raises=AssertionError)  # noqa: SC200
def test_get_argv(get_option: Any) -> None:
    """[] is substituted in options of type argv"""
    value = get_option(
        """
        [testenv]
        list_dependencies_command = foo []
        """,
        "list_dependencies_command",
        ["bar"],
    )
    assert value == ["foo", "bar"]


@pytest.mark.xfail(raises=AssertionError)  # noqa: SC200
def test_get_argv_install_command(get_option: Any) -> None:
    """[] is substituted in options of type argv_install_command"""
    value = get_option(
        """
        [testenv]
        install_command = foo [] {packages}
        """,
        "install_command",
        ["bar"],
    )
    assert value == ["foo", "bar", "{packages}"]


def test_get_string(get_option: Any) -> None:
    """[] is not substituted in options of type string"""
    value = get_option(
        """
        [testenv]
        description = []
        """,
        "description",
    )
    assert value == "[]"


@pytest.mark.parametrize(
    ("value", "result"),
    [
        ("x[]", "x[]"),  # no substitution inside a word
        ("[]x", "[]x"),  # no substitution inside a word
        pytest.param(
            "{envname}[]", "pythonbar", marks=pytest.mark.xfail(raises=AssertionError)  # noqa: SC200
        ),  # noqa: SC100 {envname} and [] are two separate words
        pytest.param(
            "[]{envname}", "barpython", marks=pytest.mark.xfail(raises=AssertionError)  # noqa: SC200
        ),  # noqa: SC100, SC200 {envname} and [] are two separate words
    ],
)
def test_examples(value: str, result: str, get_option: Any) -> None:
    got = get_option(
        """
        [testenv]
        list_dependencies_command = foo %s
        """
        % value,
        "list_dependencies_command",
        ["bar"],
    )
    assert got == ["foo", result]


@pytest.mark.xfail(raises=AssertionError)  # noqa: SC200
def test_no_substitutions_inside_pos_args(get_option: Any) -> None:
    got = get_option(
        """
        [testenv]
        list_dependencies_command = foo []
        """,
        "list_dependencies_command",
        ["{envname}"],
    )
    assert got == ["foo", "{envname}"]


def test_no_pos_args_inside_substitutions(get_option: Any, monkeypatch: Any) -> None:
    monkeypatch.setenv("BAZ", "[]")
    got = get_option(
        """
        [testenv]
        list_dependencies_command = foo {env:BAZ}
        """,
        "list_dependencies_command",
        ["bar"],
    )
    assert got == ["foo", "[]"]
