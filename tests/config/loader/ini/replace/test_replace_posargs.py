from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Final

import pytest

from tox.config.types import Command

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.config.loader.conftest import ReplaceOne
    from tox.pytest import ToxProjectCreator, ToxRunOutcome


@pytest.mark.parametrize("syntax", ["{posargs}", "[]"])
def test_replace_pos_args_none_sys_argv(syntax: str, replace_one: ReplaceOne) -> None:
    result = replace_one(syntax, None)
    assert not result


@pytest.mark.parametrize("syntax", ["{posargs}", "[]"])
def test_replace_pos_args_empty_sys_argv(syntax: str, replace_one: ReplaceOne) -> None:
    result = replace_one(syntax, [])
    assert not result


@pytest.mark.parametrize("syntax", ["{posargs}", "[]"])
def test_replace_pos_args_extra_sys_argv(syntax: str, replace_one: ReplaceOne) -> None:
    result = replace_one(syntax, [sys.executable, "magic"])
    assert result == f"{sys.executable} magic"


@pytest.mark.parametrize("syntax", ["{posargs}", "[]"])
def test_replace_pos_args(syntax: str, replace_one: ReplaceOne) -> None:
    result = replace_one(syntax, ["ok", "what", " yes "])
    assert result == "ok what ' yes '"


@pytest.mark.parametrize(
    ("value", "result"),
    [
        ("magic", "magic"),
        ("magic:colon", "magic:colon"),
        ("magic\n b c", "magic\nb c"),  # an unescaped newline keeps the newline
        ("magi\\\n c d", "magic d"),  # an escaped newline merges the lines
        ("\\{a\\}", "{a}"),  # escaped curly braces
    ],
)
def test_replace_pos_args_default(replace_one: ReplaceOne, value: str, result: str) -> None:
    outcome = replace_one(f"{{posargs:{value}}}", None)
    assert result == outcome


@pytest.mark.parametrize(
    "value",
    [
        "\\{posargs}",
        "{posargs\\}",
        "\\{posargs\\}",
        "{\\{posargs}",
        "{\\{posargs}{}",
        "\\[]",
        "[\\]",
        "\\[\\]",
    ],
)
def test_replace_pos_args_escaped(replace_one: ReplaceOne, value: str) -> None:
    result = replace_one(value, None)
    outcome = value.replace("\\", "")
    assert result == outcome


@pytest.mark.parametrize(
    ("value", "result"),
    [
        ("[]-{posargs}", "foo-foo"),
        ("{posargs}-[]", "foo-foo"),
    ],
)
def test_replace_mixed_brackets_and_braces(replace_one: ReplaceOne, value: str, result: str) -> None:
    outcome = replace_one(value, ["foo"])
    assert result == outcome


def test_half_escaped_braces(replace_one: ReplaceOne) -> None:
    """See https://github.com/tox-dev/tox/issues/1956"""
    outcome = replace_one(r"\{posargs} {posargs}", ["foo"])
    assert outcome == "{posargs} foo"


@pytest.mark.parametrize("platform", [pytest.param("win32", id="windows"), pytest.param("linux", id="linux")])
@pytest.mark.parametrize(
    "arg",
    [
        pytest.param("'x'", id="single-quoted"),
        pytest.param('"x"', id="double-quoted"),
        pytest.param("it's", id="apostrophe"),
        pytest.param("a b", id="space"),
        pytest.param("", id="empty"),
        pytest.param(r"C:\Program Files\x", id="windows-path"),
        pytest.param(r"\\server\share", id="unc-path"),
        pytest.param(r"a\\b", id="backslash-pair"),
        pytest.param("{env_name}", id="substitution"),
        pytest.param("{posargs} -x", id="posargs"),
        pytest.param("a[]b", id="brackets"),
        pytest.param(r"\{a\}", id="escaped-braces"),
    ],
)
def test_replace_pos_args_reach_command_intact(
    tox_project: ToxProjectCreator, mocker: MockerFixture, platform: str, arg: str
) -> None:
    for module in ("tox.config.loader.replacer", "tox.config.loader.str_convert"):
        mocker.patch(f"{module}.sys", mocker.create_autospec(sys, platform=platform))
    project = tox_project({"tox.ini": "[testenv]\ncommands = python {posargs}"})
    outcome = project.run("c", "-k", "commands", "--", arg)
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", arg])]


def test_replace_pos_args_quoted_command_default_keeps_author_quotes(tox_project: ToxProjectCreator) -> None:
    outcome: Final[ToxRunOutcome] = tox_project({
        "tox.ini": '[testenv]\ncommands = python -c "print({posargs:\\"hello\\"})"'
    }).run("c", "-k", "commands")
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", "-c", 'print("hello")'])]


@pytest.mark.parametrize("platform", [pytest.param("linux", id="linux"), pytest.param("win32", id="windows")])
@pytest.mark.parametrize(
    "command",
    [
        pytest.param("--filter='{posargs}'", id="single"),
        pytest.param('--filter="{posargs}"', id="double"),
    ],
)
def test_replace_pos_args_within_quoted_command_argument_stays_intact(
    tox_project: ToxProjectCreator, mocker: MockerFixture, platform: str, command: str
) -> None:
    for module in ("tox.config.loader.replacer", "tox.config.loader.str_convert"):
        mocker.patch(f"{module}.sys", mocker.create_autospec(sys, platform=platform))
    outcome: Final[ToxRunOutcome] = tox_project({"tox.ini": f"[testenv]\ncommands = tool {command}"}).run(
        "c", "-k", "commands", "--", "smoke --added-option"
    )
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["tool", "--filter=smoke --added-option"])]


@pytest.mark.parametrize(
    "arg",
    [pytest.param("{env_name}", id="env-name"), pytest.param("{posargs} -x", id="posargs")],
)
def test_replace_pos_args_within_quoted_command_argument_keeps_braces(tox_project: ToxProjectCreator, arg: str) -> None:
    outcome: Final[ToxRunOutcome] = tox_project({"tox.ini": '[testenv]\ncommands = tool "--filter={posargs}"'}).run(
        "c", "-k", "commands", "--", arg
    )
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["tool", f"--filter={arg}"])]


@pytest.mark.parametrize(
    "config",
    [
        pytest.param("commands = python {[base]args}\n[base]\nargs = {posargs}", id="section-reference"),
        pytest.param("commands = {[base]commands}\n[base]\ncommands = python {posargs}", id="section-reference-line"),
        pytest.param("description = {posargs}\ncommands = python {description}", id="key-reference"),
        pytest.param("commands = python {missing:{posargs}}", id="key-reference-default"),
        pytest.param("set_env = ARGS={posargs}\ncommands = python {env:ARGS}", id="set-env"),
        pytest.param("commands = python {env:MISSING:{posargs}}", id="env-default"),
        pytest.param("commands = python {tty:{posargs}:{posargs}}", id="tty"),
        pytest.param("commands = python {glob:missing/*:{posargs}}", id="glob-default"),
    ],
)
@pytest.mark.parametrize("arg", ["{env_name}", "{posargs} -x"])
def test_replace_pos_args_reach_command_intact_when_nested(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch, config: str, arg: str
) -> None:
    monkeypatch.delenv("MISSING", raising=False)
    project: Final = tox_project({"tox.ini": f"[testenv]\n{config}"})
    outcome: Final = project.run("c", "-k", "commands", "--", arg)
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", arg])]


def test_replace_pos_args_default_substituted(tox_project: ToxProjectCreator) -> None:
    project: Final = tox_project({
        "tox.ini": "[testenv]\ncommands = python {posargs:{[base]args}}\n[base]\nargs = a{/}{env_name}"
    })
    outcome: Final = project.run("c", "-k", "commands")
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", f"a{os.sep}py"])]


@pytest.mark.parametrize("platform", [pytest.param("win32", id="windows"), pytest.param("linux", id="linux")])
@pytest.mark.parametrize(
    "commands",
    [
        pytest.param("{posargs}", id="alone"),
        pytest.param("[]", id="alone-brackets"),
        pytest.param("{posargs:pytest}", id="alone-default"),
        pytest.param("{env:_MISSING:{posargs}}", id="alone-nested"),
        pytest.param("python {env:_MISSING:-c} {posargs}", id="after-token"),
        pytest.param("python -c {posargs}", id="in-line"),
    ],
)
@pytest.mark.parametrize("override", [pytest.param(True, id="override"), pytest.param(False, id="config")])
def test_replace_pos_args_line_break_stays_one_command(
    tox_project: ToxProjectCreator, mocker: MockerFixture, platform: str, commands: str, override: bool
) -> None:
    for module in ("tox.config.loader.replacer", "tox.config.loader.str_convert"):
        mocker.patch(f"{module}.sys", mocker.create_autospec(sys, platform=platform))
    project: Final = tox_project({"tox.ini": f"[testenv]\ncommands = {'python' if override else commands}"})
    prefix: Final = [] if commands.startswith("python") else ["python", "-c"]
    overrides: Final = ["-x", f"testenv.commands={commands}"] if override else []
    outcome: Final = project.run("c", "-k", "commands", *overrides, "--", *prefix, "a\npython -c b\n", "\n", "c\r\nd")
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", "-c", "a python -c b", "", "c d"])]


def test_replace_pos_args_line_break_stays_one_list_entry(tox_project: ToxProjectCreator) -> None:
    project: Final = tox_project({"tox.ini": "[testenv]\nallowlist_externals = {posargs}"})
    outcome: Final = project.run("c", "-k", "allowlist_externals", "--", "a\nb")
    outcome.assert_success()
    assert outcome.env_conf("py")["allowlist_externals"] == ["'a b'"]


@pytest.mark.parametrize(
    "arg",
    [
        pytest.param("main\npython -c injected\n", id="plain"),
        pytest.param("it's\npython -c injected\n", id="apostrophe"),
    ],
)
def test_referenced_default_command_line_break_stays_one_command(tox_project: ToxProjectCreator, arg: str) -> None:
    project: Final = tox_project({
        "tox.ini": (
            "[testenv:notes]\nrunner = virtualenv-pep-723\nscript = check.py\n"
            "[testenv:release]\ncommands = python -c pass\n    {[testenv:notes]commands}\n"
        ),
        "check.py": "print('ok')\n",
    })
    outcome: Final = project.run("c", "-e", "release", "-k", "commands", "--", arg)
    outcome.assert_success()
    assert outcome.env_conf("release")["commands"] == [
        Command(args=["python", "-c", "pass"]),
        Command(args=["python", str(project.path / "check.py"), " ".join(arg.splitlines())]),
    ]


@pytest.mark.parametrize("platform", [pytest.param("win32", id="windows"), pytest.param("linux", id="linux")])
@pytest.mark.parametrize(
    "config",
    [
        pytest.param("[testenv:a]\n[testenv:py]\ncommands = {[testenv:a]commands}", id="env-reference"),
        pytest.param("[testenv:py]\ncommands_pre = python {posargs} -x\ncommands = {commands_pre}", id="key-reference"),
    ],
)
@pytest.mark.parametrize(
    "arg",
    [
        pytest.param("'x'", id="single-quoted"),
        pytest.param('"x"', id="double-quoted"),
        pytest.param("it's", id="apostrophe"),
        pytest.param("a b", id="space"),
        pytest.param("", id="empty"),
        pytest.param(r"C:\Program Files\x", id="windows-path"),
        pytest.param(r"\\server\share", id="unc-path"),
        pytest.param(r"a\\b", id="backslash-pair"),
    ],
)
def test_replace_pos_args_reach_referenced_command_intact(
    tox_project: ToxProjectCreator, mocker: MockerFixture, platform: str, config: str, arg: str
) -> None:
    for module in ("tox.config.loader.replacer", "tox.config.loader.str_convert"):
        mocker.patch(f"{module}.sys", mocker.create_autospec(sys, platform=platform))
    project: Final = tox_project({"tox.ini": f"[testenv]\ncommands = python {{posargs}} -x\n{config}"})
    outcome: Final = project.run("c", "-e", "py", "-k", "commands", "--", arg)
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", arg, "-x"])]
