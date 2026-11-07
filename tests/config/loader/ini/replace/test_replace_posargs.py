from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Final

import pytest

from tox.config.types import Command

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.config.loader.conftest import ReplaceOne
    from tox.pytest import ToxProject, ToxProjectCreator, ToxRunOutcome


@pytest.mark.parametrize(
    "syntax", [pytest.param("{posargs}", id="open-posargs-close"), pytest.param("[]", id="lbracket-rbracket")]
)
def test_replace_pos_args_none_sys_argv(syntax: str, replace_one: ReplaceOne) -> None:
    result = replace_one(syntax, None)
    assert not result


@pytest.mark.parametrize(
    "syntax", [pytest.param("{posargs}", id="open-posargs-close"), pytest.param("[]", id="lbracket-rbracket")]
)
def test_replace_pos_args_empty_sys_argv(syntax: str, replace_one: ReplaceOne) -> None:
    result = replace_one(syntax, [])
    assert not result


@pytest.mark.parametrize(
    "syntax", [pytest.param("{posargs}", id="open-posargs-close"), pytest.param("[]", id="lbracket-rbracket")]
)
def test_replace_pos_args_extra_sys_argv(syntax: str, replace_one: ReplaceOne) -> None:
    result = replace_one(syntax, [sys.executable, "magic"])
    assert result == f"{sys.executable} magic"


@pytest.mark.parametrize(
    "syntax", [pytest.param("{posargs}", id="open-posargs-close"), pytest.param("[]", id="lbracket-rbracket")]
)
def test_replace_pos_args(syntax: str, replace_one: ReplaceOne) -> None:
    result = replace_one(syntax, ["ok", "what", " yes "])
    assert result == "ok what ' yes '"


@pytest.mark.parametrize(
    ("value", "result"),
    [
        pytest.param("magic", "magic", id="magic-magic"),
        pytest.param("magic:colon", "magic:colon", id="magic-colon-colon-magic-colon-colon"),
        pytest.param(
            "magic\n b c", "magic\nb c", id="magic-newline-space-b-space-c-magic-newline-b-space-c"
        ),  # an unescaped newline keeps the newline
        pytest.param(
            "magi\\\n c d", "magic d", id="magi-backslash-newline-space-c-space-d-magic-space-d"
        ),  # an escaped newline merges the lines
        pytest.param("\\{a\\}", "{a}", id="backslash-open-a-backslash-close-open-a-close"),  # escaped curly braces
    ],
)
def test_replace_pos_args_default(replace_one: ReplaceOne, value: str, result: str) -> None:
    outcome = replace_one(f"{{posargs:{value}}}", None)
    assert result == outcome


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("\\{posargs}", id="backslash-open-posargs-close"),
        pytest.param("{posargs\\}", id="open-posargs-backslash-close"),
        pytest.param("\\{posargs\\}", id="backslash-open-posargs-backslash-close"),
        pytest.param("{\\{posargs}", id="open-backslash-open-posargs-close"),
        pytest.param("{\\{posargs}{}", id="open-backslash-open-posargs-close-open-close"),
        pytest.param("\\[]", id="backslash-lbracket-rbracket"),
        pytest.param("[\\]", id="lbracket-backslash-rbracket"),
        pytest.param("\\[\\]", id="backslash-lbracket-backslash-rbracket"),
    ],
)
def test_replace_pos_args_escaped(replace_one: ReplaceOne, value: str) -> None:
    result = replace_one(value, None)
    outcome = value.replace("\\", "")
    assert result == outcome


@pytest.mark.parametrize(
    ("value", "result"),
    [
        pytest.param("[]-{posargs}", "foo-foo", id="lbracket-rbracket-dash-open-posargs-close-foo-dash-foo"),
        pytest.param("{posargs}-[]", "foo-foo", id="open-posargs-close-dash-lbracket-rbracket-foo-dash-foo"),
    ],
)
def test_replace_mixed_brackets_and_braces(replace_one: ReplaceOne, value: str, result: str) -> None:
    outcome = replace_one(value, ["foo"])
    assert result == outcome


def test_half_escaped_braces(replace_one: ReplaceOne) -> None:
    outcome = replace_one(r"\{posargs} {posargs}", ["foo"])
    assert outcome == "{posargs} foo"


_LINE_BREAK_COMMANDS: Final = pytest.mark.parametrize(
    ("commands", "prefix"),
    [
        pytest.param("{posargs}", ["python", "-c"], id="alone"),
        pytest.param("[]", ["python", "-c"], id="alone-brackets"),
        pytest.param("{posargs:pytest}", ["python", "-c"], id="alone-default"),
        pytest.param("{env:_MISSING:{posargs}}", ["python", "-c"], id="alone-nested"),
        pytest.param("python {env:_MISSING:-c} {posargs}", [], id="after-token"),
        pytest.param("python -c {posargs}", [], id="in-line"),
    ],
)


@pytest.mark.parametrize("platform", [pytest.param("win32", id="windows"), pytest.param("linux", id="linux")])
@_LINE_BREAK_COMMANDS
def test_replace_pos_args_line_break_stays_one_command(
    tox_project: ToxProjectCreator, mocker: MockerFixture, platform: str, commands: str, prefix: list[str]
) -> None:
    for module in ("tox.config.loader.replacer", "tox.config.loader.str_convert"):
        mocker.patch(f"{module}.sys", mocker.create_autospec(sys, platform=platform))
    project: Final[ToxProject] = tox_project({"tox.ini": f"[testenv]\ncommands = {commands}"})
    outcome: Final[ToxRunOutcome] = project.run(
        "c", "-k", "commands", "--", *prefix, "a\npython -c b\n", "\n", "c\r\nd"
    )
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", "-c", "a python -c b", "", "c d"])]


@pytest.mark.parametrize("platform", [pytest.param("win32", id="windows"), pytest.param("linux", id="linux")])
@_LINE_BREAK_COMMANDS
def test_replace_pos_args_line_break_stays_one_command_from_override(
    tox_project: ToxProjectCreator, mocker: MockerFixture, platform: str, commands: str, prefix: list[str]
) -> None:
    for module in ("tox.config.loader.replacer", "tox.config.loader.str_convert"):
        mocker.patch(f"{module}.sys", mocker.create_autospec(sys, platform=platform))
    project: Final[ToxProject] = tox_project({"tox.ini": "[testenv]\ncommands = python"})
    outcome: Final[ToxRunOutcome] = project.run(
        "c", "-k", "commands", "-x", f"testenv.commands={commands}", "--", *prefix, "a\npython -c b\n", "\n", "c\r\nd"
    )
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", "-c", "a python -c b", "", "c d"])]


def test_replace_pos_args_line_break_stays_one_list_entry(tox_project: ToxProjectCreator) -> None:
    project: Final[ToxProject] = tox_project({"tox.ini": "[testenv]\nallowlist_externals = {posargs}"})
    outcome: Final[ToxRunOutcome] = project.run("c", "-k", "allowlist_externals", "--", "a\nb")
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
    project: Final[ToxProject] = tox_project({
        "tox.ini": (
            "[testenv:notes]\nrunner = virtualenv-pep-723\nscript = check.py\n"
            "[testenv:release]\ncommands = python -c pass\n    {[testenv:notes]commands}\n"
        ),
        "check.py": "print('ok')\n",
    })
    outcome: Final[ToxRunOutcome] = project.run("c", "-e", "release", "-k", "commands", "--", arg)
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
    project: Final[ToxProject] = tox_project({"tox.ini": f"[testenv]\ncommands = python {{posargs}} -x\n{config}"})
    outcome: Final[ToxRunOutcome] = project.run("c", "-e", "py", "-k", "commands", "--", arg)
    outcome.assert_success()
    assert outcome.env_conf("py")["commands"] == [Command(args=["python", arg, "-x"])]
