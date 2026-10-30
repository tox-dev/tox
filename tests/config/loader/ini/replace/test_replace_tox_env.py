from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Final

import pytest
from packaging.requirements import Requirement

from tox.config.loader.api import Override
from tox.config.loader.replacer import MAX_REPLACE_DEPTH
from tox.config.sets import ConfigSet
from tox.config.types import Command, EnvList
from tox.report import HandledError

if TYPE_CHECKING:
    from types import UnionType

    from tests.config.loader.conftest import ReplaceOne
    from tests.conftest import ToxIniCreator
    from tox.pytest import LogCaptureFixture, MonkeyPatch, ToxProject, ToxProjectCreator, ToxRunOutcome

EnvConfigCreator = Callable[[str], ConfigSet]


@pytest.fixture
def example(tox_ini_conf: ToxIniCreator) -> EnvConfigCreator:
    def func(conf: str) -> ConfigSet:
        config = tox_ini_conf(f"""[tox]\nenv_list = a\n[testenv]\n{conf}\n""")
        return config.get_env("a")

    return func


def test_replace_within_tox_env(example: EnvConfigCreator) -> None:
    env_config = example("r = 1\no = {r}")
    env_config.add_config(keys="r", of_type=str, default="r", desc="r")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "1"


def test_replace_within_tox_env_chain(example: EnvConfigCreator) -> None:
    env_config = example("r = 1\no = {r}/2\np = {r} {o}")
    env_config.add_config(keys="r", of_type=str, default="r", desc="r")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    env_config.add_config(keys="p", of_type=str, default="p", desc="p")
    result = env_config["p"]
    assert result == "1 1/2"


def test_replace_within_section_chain(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf("[vars]\na = 1\nb = {[vars]a}/2\nc = {[vars]a}/3\n[testenv:a]\nd = {[vars]b} {[vars]c}")
    env_config = config.get_env("a")
    env_config.add_config(keys="d", of_type=str, default="d", desc="d")
    result = env_config["d"]
    assert result == "1/2 1/3"


@pytest.fixture
def load_commands(tox_ini_conf: ToxIniCreator) -> Callable[[str], list[list[str]]]:
    def func(commands: str) -> list[list[str]]:
        config = tox_ini_conf(
            "[testenv:x]\ndeps =\n  requests\n  pytest>=8\ncommands =\n  pip install {[testenv:x]deps}\n  python -V\n"
            'title = title {env:TITLE}\nquoted = tool "title {env:TITLE}"\n'
            f"[testenv:a]\ncommands = {commands}\n"
        )
        env_config = config.get_env("a")
        env_config.add_config(keys="commands", of_type=list[Command], default=[], desc="commands")
        return [command.args for command in env_config["commands"]]

    return func


def test_replace_section_alone_on_command_line_expands_to_commands(
    load_commands: Callable[[str], list[list[str]]],
) -> None:
    commands = load_commands("{[testenv:x]commands}\n  python -c pass")
    assert commands == [["pip", "install", "requests", "pytest>=8"], ["python", "-V"], ["python", "-c", "pass"]]


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        pytest.param("pip install {[testenv:x]deps}", ["pip", "install", "requests", "pytest>=8"], id="text-before"),
        pytest.param("{[testenv:x]deps} --pre", ["requests", "pytest>=8", "--pre"], id="text-after"),
        pytest.param("{[testenv:x]deps}{posargs}", ["requests", "pytest>=8"], id="beside-substitution"),
        pytest.param(
            "echo {[testenv:x]commands}",
            ["echo", "pip", "install", "requests", "pytest>=8", "python", "-V"],
            id="echo-commands",
        ),
    ],
)
def test_replace_section_within_command_line_joins_arguments(
    load_commands: Callable[[str], list[list[str]]], command: str, expected: list[str]
) -> None:
    assert load_commands(command) == [expected]


@pytest.mark.parametrize("platform", [pytest.param("linux", id="linux"), pytest.param("win32", id="windows")])
@pytest.mark.parametrize(
    "value",
    [
        pytest.param('fix" --option "typo', id="double-quotes"),
        pytest.param("fix' --option 'typo", id="single-quotes"),
        pytest.param("it's", id="apostrophe"),
        pytest.param(r"a\b", id="backslash"),
        pytest.param(r"a\\b", id="two-backslashes"),
        pytest.param(r"a\" --option \"b", id="escaped-double-quotes"),
        pytest.param(r'a\\" --option "b', id="double-quotes-after-two-backslashes"),
        pytest.param("a\\", id="trailing-backslash"),
    ],
)
@pytest.mark.parametrize(
    ("command", "expected"),
    [
        pytest.param('tool "--title={env:TITLE}" end', "--title=TITLE", id="double"),
        pytest.param("tool '--title={env:TITLE}' end", "--title=TITLE", id="single"),
        pytest.param("tool --title=\"a {env:TITLE}\"' {env:TITLE}' end", "--title=a TITLE TITLE", id="adjacent"),
        pytest.param('tool "{env:MISSING:{env:TITLE}}" end', "TITLE", id="default"),
        pytest.param('tool "{[testenv:x]title}" end', "title TITLE", id="reference"),
        pytest.param("{[testenv:x]quoted} end", "title TITLE", id="quoted-by-reference"),
        pytest.param("""tool '{"title": "{env:TITLE}"}' end""", '{"title": "TITLE"}', id="single-braces"),
        pytest.param(r"""tool "{\"title\": \"{env:TITLE}\"}" end""", '{"title": "TITLE"}', id="double-braces"),
    ],
)
def test_replace_within_quoted_command_argument_stays_within(
    load_commands: Callable[[str], list[list[str]]],
    monkeypatch: MonkeyPatch,
    command: str,
    expected: str,
    value: str,
    platform: str,
) -> None:
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setenv("TITLE", value)
    assert load_commands(command) == [["tool", expected.replace("TITLE", value), "end"]]


def test_replace_nested_env_value_within_quoted_command_argument_stays_within(
    load_commands: Callable[[str], list[list[str]]], monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("TITLE", "{env:TITLE_PART}")
    monkeypatch.setenv("TITLE_PART", 'fix" --option "typo')
    assert load_commands('tool "--title={env:TITLE}" end') == [["tool", '--title=fix" --option "typo', "end"]]


def test_replace_within_quoted_command_argument_joins_lines(
    load_commands: Callable[[str], list[list[str]]], monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("TITLE", 'a\nb" c')
    assert load_commands('tool "{env:TITLE} {env:TITLE} {env:TITLE}"') == [["tool", 'a b" c a b" c a b" c']]


def test_replace_command_quote_ends_with_line(
    load_commands: Callable[[str], list[list[str]]], monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("TITLE", 'fix" --option "typo')
    assert load_commands('echo it\'s\n  tool "{env:TITLE}"') == [["echo", "it's"], ["tool", 'fix" --option "typo']]


def test_replace_outside_quoted_command_argument_splits(
    load_commands: Callable[[str], list[list[str]]], monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGS", "-a 'b c'")
    assert load_commands('tool "a" {env:ARGS}') == [["tool", "a", "-a", "b c"]]


def test_replace_kept_within_quoted_command_argument(load_commands: Callable[[str], list[list[str]]]) -> None:
    assert load_commands(r'''python -c "print({\"a\": 1})"''') == [["python", "-c", 'print({"a": 1})']]


def test_replace_quoted_command_default_keeps_author_quotes(
    load_commands: Callable[[str], list[list[str]]], monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.delenv("MSG", raising=False)
    assert load_commands(r'python -c "print({env:MSG:\"hello\"})"') == [["python", "-c", 'print("hello")']]


def test_replace_quoted_command_default_keeps_colons(
    load_commands: Callable[[str], list[list[str]]], monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.delenv("MISSING", raising=False)
    assert load_commands('tool "{env:MISSING:a:b}"') == [["tool", "a:b"]]


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        pytest.param(r'python -c "print({tty:unused:\"bye\"})"', 'print("bye")', id="tty"),
        pytest.param(r'python -c "print({glob:no-such-file:\"hello\"})"', 'print("hello")', id="glob"),
        pytest.param(r'python -c "print({factor:unknown:\"hello\"})"', 'print("hello")', id="factor"),
        pytest.param(r'python -c "print({missing:\"hello\"})"', 'print("hello")', id="reference"),
    ],
)
def test_replace_quoted_command_other_defaults_keep_author_quotes(
    load_commands: Callable[[str], list[list[str]]], command: str, expected: str
) -> None:
    assert load_commands(command) == [["python", "-c", expected]]


def test_replace_quoted_command_windows_glob_default_keeps_author_quotes(
    load_commands: Callable[[str], list[list[str]]], monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    assert load_commands(r'python -c "print({glob:C:/no-such-file:\"hello\"})"') == [["python", "-c", 'print("hello")']]


def test_replace_within_quoted_argument_of_single_command(
    tox_ini_conf: ToxIniCreator, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("TITLE", 'fix" --option "typo')
    env_config: Final[ConfigSet] = tox_ini_conf('[testenv:a]\ncommand = tool "--title={env:TITLE}" {packages}').get_env(
        "a"
    )
    env_config.add_config(keys="command", of_type=Command, default=Command(["tool"]), desc="command")
    assert env_config["command"].args == ["tool", '--title=fix" --option "typo', "{packages}"]


def test_override_quoted_command_lines_stay_intact(quoted_command_override: ConfigSet) -> None:
    quoted_command_override.add_config(keys="commands", of_type=list[Command], default=[], desc="commands")
    assert quoted_command_override["commands"] == [Command(args=["tool", '--title=fix" --option "typo'])]


@pytest.fixture
def quoted_command_override(tox_ini_conf: ToxIniCreator, monkeypatch: MonkeyPatch) -> ConfigSet:
    monkeypatch.setenv("TITLE", 'fix" --option "typo')
    return tox_ini_conf(
        "[testenv:a]\ncommands = tool old\ncommand = tool old",
        override=[
            Override('testenv:a.commands=tool "--title={env:TITLE}"'),
            Override('testenv:a.command=tool "--title={env:TITLE}"'),
        ],
    ).get_env("a")


def test_override_quoted_single_command_stays_intact(quoted_command_override: ConfigSet) -> None:
    quoted_command_override.add_config(keys="command", of_type=Command, default=Command(args=["tool"]), desc="command")
    assert quoted_command_override["command"] == Command(args=["tool", '--title=fix" --option "typo'])


@pytest.fixture
def load_list(tox_ini_conf: ToxIniCreator, monkeypatch: pytest.MonkeyPatch) -> Callable[[str, str], list[str]]:
    def func(entries: str, value: str) -> list[str]:
        monkeypatch.setenv("VALUE", value)
        env_config: Final[ConfigSet] = tox_ini_conf(
            f"[x]\nvalue = {{env:VALUE}}\nentry = c{{env:VALUE}}\n[testenv:a]\nentries = {entries}\n"
        ).get_env("a")
        env_config.add_config(keys="entries", of_type=list[str], default=[], desc="entries")
        return env_config["entries"]

    return func


@pytest.mark.parametrize(
    ("entries", "value", "expected"),
    [
        pytest.param("{env:VALUE}", "a,b", ["a", "b"], id="only"),
        pytest.param("x, {env:VALUE} ,y", "a,b", ["x", "a", "b", "y"], id="between-commas"),
        pytest.param("x\n  {env:VALUE}\n  y", "a\nb", ["x", "a", "b", "y"], id="between-lines"),
        pytest.param("x, {[x]value}", "a,b", ["x", "a", "b"], id="reference"),
        pytest.param("x, {env:MISSING:{env:VALUE}}", "a,b", ["x", "a", "b"], id="nested"),
    ],
)
def test_replace_alone_in_list_entry_expands_to_entries(
    load_list: Callable[[str, str], list[str]], entries: str, value: str, expected: list[str]
) -> None:
    assert load_list(entries, value) == expected


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        pytest.param("x, a{env:VALUE}", ["x", "a>=1"], id="text-before"),
        pytest.param("{env:VALUE}a, x", [">=1a", "x"], id="text-after"),
        pytest.param("x, {[x]entry}", ["x", "c>=1"], id="referenced"),
    ],
)
def test_replace_within_list_entry_is_part_of_entry(
    load_list: Callable[[str, str], list[str]], entries: str, expected: list[str]
) -> None:
    assert load_list(entries, ">=1") == expected


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        pytest.param("\n  a{env:VALUE}\n  x", ["a>=1,<2", "x"], id="text-before"),
        pytest.param("\n  {[x]entry}\n  x", ["c>=1,<2", "x"], id="referenced"),
        pytest.param("\n  {env:MISSING:a{env:VALUE}}\n  x", ["a>=1,<2", "x"], id="nested"),
    ],
)
def test_replace_within_list_line_keeps_comma(
    load_list: Callable[[str, str], list[str]], entries: str, expected: list[str]
) -> None:
    assert load_list(entries, ">=1,<2") == expected


@pytest.mark.parametrize(
    ("entries", "value"),
    [
        pytest.param("a{env:VALUE}", "1,evil", id="only"),
        pytest.param("x, a{env:VALUE}", "1,evil", id="text-before"),
        pytest.param("{env:VALUE}a, x", "evil,1", id="text-after"),
        pytest.param("{env:MISSING:a}{env:VALUE}", "1,evil", id="beside-substitution"),
        pytest.param("{env:MISSING:a} {env:VALUE}", "1,evil", id="blank-after-substitution"),
        pytest.param("x, a{[x]value}", "1,evil", id="reference"),
        pytest.param("x, {[x]entry}", "1,evil", id="referenced"),
        pytest.param("x, {env:MISSING:a{env:VALUE}}", "1,evil", id="nested"),
        pytest.param("x, a{env:VALUE}", "1\nevil", id="line-break"),
        pytest.param("\n  a{env:VALUE}\n  x", "1\nevil", id="line-break-within-line"),
        pytest.param("\n  {[x]entry}\n  x", "1\nevil", id="line-break-referenced"),
    ],
)
def test_replace_within_list_entry_cannot_add_entries(
    load_list: Callable[[str, str], list[str]], entries: str, value: str
) -> None:
    with pytest.raises(HandledError, match=r"replace failed in a\.entries .* cannot add an entry separator"):
        load_list(entries, value)


@pytest.mark.parametrize("of_type", [set[str], list[Requirement], list[str] | str, list[str] | None])
def test_replace_within_entry_cannot_add_entries_for_type(
    example: EnvConfigCreator, monkeypatch: pytest.MonkeyPatch, of_type: type[object] | UnionType
) -> None:
    monkeypatch.setenv("VALUE", "1,evil")
    env_config: Final[ConfigSet] = example("entries = a=={env:VALUE}")
    env_config.add_config(keys="entries", of_type=of_type, default=None, desc="entries")
    with pytest.raises(HandledError, match=r"replace failed in a\.entries .* cannot add an entry separator"):
        env_config["entries"]


def test_replace_within_dict_entry_cannot_add_setting(
    example: EnvConfigCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VALUE", "7\ninjected-setting=chosen")
    env_config: Final[ConfigSet] = example("settings = build-tag={env:VALUE}")
    env_config.add_config(keys="settings", of_type=dict[str, str], default={}, desc="settings")
    with pytest.raises(HandledError, match=r"replace failed in a\.settings .* cannot add an entry separator"):
        env_config["settings"]


def test_replace_within_dict_entry_accepts_value(example: EnvConfigCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VALUE", "7")
    env_config: Final[ConfigSet] = example("settings = build-tag={env:VALUE}")
    env_config.add_config(keys="settings", of_type=dict[str, str], default={}, desc="settings")
    assert env_config["settings"] == {"build-tag": "7"}


def test_replace_alone_in_dict_entry_can_expand(example: EnvConfigCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VALUE", "build-tag=7\nother=one")
    env_config: Final[ConfigSet] = example("settings = {env:VALUE}")
    env_config.add_config(keys="settings", of_type=dict[str, str], default={}, desc="settings")
    assert env_config["settings"] == {"build-tag": "7", "other": "one"}


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("sqlite,release", id="comma"),
        pytest.param("sqlite\nrelease", id="line-break"),
        pytest.param("sqlite{,release}", id="factor-group"),
    ],
)
def test_replace_within_env_list_entry_cannot_add_environment(
    tox_ini_conf: ToxIniCreator, monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("BACKEND", value)
    with pytest.raises(HandledError, match=r"replace failed in tox\.env_list .* cannot add an entry separator"):
        tox_ini_conf("[tox]\nenv_list = lint, unit-{env:BACKEND}").core["env_list"]


def test_replace_alone_in_env_list_entry_can_expand(
    tox_ini_conf: ToxIniCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BACKEND", "lint,release")
    assert tox_ini_conf("[tox]\nenv_list = {env:BACKEND}").core["env_list"] == EnvList(["lint", "release"])


@pytest.mark.timeout(5)
def test_replace_list_circular_fan_out_stops(example: EnvConfigCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAGIC", "{env:MAGIC}" * 100)
    env_config: Final = example("items = {env:MAGIC}")
    env_config.add_config(keys="items", of_type=list[str], default=[], desc="items")

    assert len("{env:MAGIC}") < len(env_config["items"][0]) < 1_000_000


def test_replace_within_env_list_entry_accepts_value(
    tox_ini_conf: ToxIniCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BACKEND", "sqlite")
    assert tox_ini_conf("[tox]\nenv_list = lint, unit-{env:BACKEND}").core["env_list"] == EnvList([
        "lint",
        "unit-sqlite",
    ])


@pytest.mark.parametrize("depth", [5, 99, 100, 101, 150, 256])
def test_replace_within_section_chain_deep(caplog: LogCaptureFixture, tox_ini_conf: ToxIniCreator, depth: int) -> None:
    config = tox_ini_conf(
        "\n".join(
            [
                "[vars]",
                "a0 = 1",
                *(f"a{ix} = {{[vars]a{ix - 1}}}" for ix in range(1, depth + 1)),
                "[testenv:a]",
                f"b = {{[vars]a{depth}}}",
            ],
        ),
    )
    env_config = config.get_env("a")
    env_config.add_config(keys="b", of_type=str, default="b", desc="b")
    result = env_config["b"]
    if depth > MAX_REPLACE_DEPTH:
        exp_stopped_at = "{[vars]a%s}" % (depth - MAX_REPLACE_DEPTH - 1)
        assert result == exp_stopped_at
        assert f"Could not expand {exp_stopped_at} after recursing {MAX_REPLACE_DEPTH + 1} frames" in caplog.messages
    else:
        assert result == "1"


def test_replace_command_section_chain_stops_at_depth(caplog: LogCaptureFixture, tox_ini_conf: ToxIniCreator) -> None:
    config: Final = tox_ini_conf(
        "\n".join(
            [
                "[vars]",
                "a0 = 1",
                *(f"a{ix} = {{[vars]a{ix - 1}}}" for ix in range(1, MAX_REPLACE_DEPTH + 2)),
                "[testenv:a]",
                f"commands = echo {{[vars]a{MAX_REPLACE_DEPTH + 1}}} {{env:MAGIC}}",
            ],
        ),
    )
    env_config: Final[ConfigSet] = config.get_env("a")
    env_config.add_config(keys="commands", of_type=list[Command], default=[], desc="commands")

    assert [command.args for command in env_config["commands"]] == [["echo", "{[vars]a0}", "{env:MAGIC}"]]
    assert f"after recursing {MAX_REPLACE_DEPTH + 1} frames" in "\n".join(caplog.messages)


def test_replace_within_tox_env_missing_raises(example: EnvConfigCreator) -> None:
    env_config = example("o = {p}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")

    assert env_config["o"] == "{p}"


def test_replace_within_tox_env_missing_default(example: EnvConfigCreator) -> None:
    env_config = example("o = {p:one}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_within_tox_env_missing_default_env_only(example: EnvConfigCreator) -> None:
    env_config = example("o = {[testenv:a]p:one}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_within_tox_env_missing_no_default(example: EnvConfigCreator) -> None:
    env_config = example("o = {[testenv:b]p}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    assert env_config["o"] == "{[testenv:b]p}"


def test_replace_within_tox_env_from_base(example: EnvConfigCreator) -> None:
    env_config = example("p = one\n[testenv:a]\no = {[testenv]p}")
    env_config.add_config(keys="p", of_type=str, default="p", desc="p")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_ref_raw_value(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf("[testenv:a]\nx = {[testenv:b]v}\n[testenv:b]\nv=1")

    class BadType:
        def __init__(self, value: str) -> None:
            if value != "magic":
                raise ValueError(value)

    conf_b = config.get_env("b")
    conf_b.add_config(keys="v", of_type=BadType, default=BadType("magic"), desc="p")

    conf_a = config.get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")

    assert conf_a["x"] == "1"


@pytest.mark.parametrize(
    ("start", "end"),
    [
        ("0", "0"),
        ("0}", "0}"),
        ("{0", "{0"),
        ("{0}", "{0}"),
        ("{}{0}", "{}{0}"),
        ("{0}{}", "{0}{}"),
        ("\\{0}", "{0}"),
        ("{0\\}", "{0}"),
        ("\\{0\\}", "{0}"),
        ("f\\{0\\}", "f{0}"),
        ("\\{0\\}f", "{0}f"),
        ("\\{\\{0", "{{0"),
        ("0\\}\\}", "0}}"),
        ("\\{\\{0\\}\\}", "{{0}}"),
    ],
)
def test_do_not_replace(replace_one: ReplaceOne, start: str, end: str) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    value = replace_one(start)
    assert value == end


def test_replace_from_tox_section_non_registered(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[tox]\na=1\n[testenv:a]\nx = {[tox]a}").get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")
    assert conf_a["x"] == "1"


def test_replace_from_tox_section_missing_section(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:a]\nx = {[magic]a}").get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")
    assert conf_a["x"] == "{[magic]a}"


def test_replace_from_tox_section_key_with_dash(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:a]\nx = {[magic]a-b}\n[magic]\na-b=1").get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")
    assert conf_a["x"] == "1"


def test_replace_circular(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:a]\nx = {y}\ny = {x}").get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")
    conf_a.add_config(keys="y", of_type=str, default="n", desc="n")
    with pytest.raises(HandledError) as exc:
        assert conf_a["x"]
    assert "circular chain detected testenv:a.x, testenv:a.y" in str(exc.value)


def test_replace_from_tox_section_missing_value(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:e]\nx = {[m]a}\n[m]").get_env("e")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="d")
    assert conf_a["x"] == "{[m]a}"


def test_replace_from_section_bad_type(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:e]\nx = {[m]a}\n[m]\na=w\n").get_env("e")
    conf_a.add_config(keys="x", of_type=int, default=1, desc="d")
    with pytest.raises(HandledError, match=r"failed to load e\.x: invalid literal.*w.*"):
        assert conf_a["x"]


def test_replace_from_tox_section_registered(tox_ini_conf: ToxIniCreator, tmp_path: Path) -> None:
    conf_a = tox_ini_conf("[testenv:a]\nx = {[tox]tox_root}").get_env("a")
    conf_a.add_config(keys="x", of_type=Path, default=Path.cwd() / "magic", desc="d")
    assert conf_a["x"] == (tmp_path / "c")


def test_replace_from_tox_other_tox_section_same_name(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:a]\nx={[testenv:b]c}\nc=d\n[testenv:b]}").get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="", desc="d")
    assert conf_a["x"] == "{[testenv:b]c}"


@pytest.mark.parametrize(
    ("env_name", "exp"),
    [
        ("testenv:foobar", "1"),
        ("testenv:foo-bar", "1"),
        ("foo-bar", "1"),
        ("foobar", "1"),
    ],
)
def test_replace_valid_section_names(tox_ini_conf: ToxIniCreator, env_name: str, exp: str) -> None:
    conf_a = tox_ini_conf(f"[{env_name}]\na={exp}\n[testenv:a]\nx = {{[{env_name}]a}}").get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")
    assert conf_a["x"] == exp


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        pytest.param("testenv.extras=BLUE", "BLUE GREEN", id="replace"),
        pytest.param("testenv.extras+=BLUE", "RED\nBLUE GREEN", id="append"),
    ],
)
def test_override_propagates_through_section_ref(tox_ini_conf: ToxIniCreator, override: str, expected: str) -> None:
    """An override on a base section propagates through a ``{[section]key}`` reference (#3950)."""
    config = tox_ini_conf(
        dedent("""
            [testenv]
            extras = RED
            [testenv:test]
            extras = {[testenv]extras} GREEN
            """),
        override=[Override(override)],
    )

    env_config = config.get_env("test")
    env_config.add_config(keys="extras", of_type=str, default="", desc="extras")
    assert env_config["extras"] == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("plain", id="plain"),
        pytest.param("my proj", id="space"),
        pytest.param("my  proj", id="spaces"),
        pytest.param("o'brien", id="single-quote"),
        pytest.param('q"uote', id="double-quote"),
        pytest.param("back\\slash", id="backslash"),
        pytest.param("C:\\my dir\\", id="trailing-backslash"),
        pytest.param(r"\\server\my share", id="unc-path"),
        pytest.param("a#b", id="comment"),
        pytest.param("{env_name}", id="substitution"),
    ],
)
@pytest.mark.parametrize(
    ("config", "expected"),
    [
        pytest.param("c = python {p} -x", "{}", id="bare"),
        pytest.param("c = python {p}/a -x", "{}/a", id="suffix"),
        pytest.param("c = python --opt={p} -x", "--opt={}", id="option"),
        pytest.param("c = python {p}{:}{p} -x", f"{{}}{os.pathsep}{{}}", id="twice"),
        pytest.param('c = python "{p}" -x', "{}", id="double"),
        pytest.param("c = python '{p}/a' -x", "{}/a", id="single"),
        pytest.param('c = python "it\'s {p} !" -x', "it's {} !", id="text"),
        pytest.param("c = python {env:MISSING:{p}/a} -x", "{}/a", id="env-default"),
        pytest.param("c = python {missing:{p}/a} -x", "{}/a", id="key-default"),
        pytest.param("c = python {[base]args} -x\n[base]\nargs = {p}/a", "{}/a", id="reference"),
        pytest.param("c = python '{[base]args}' -x\n[base]\nargs = {p}/a", "{}/a", id="reference-quoted"),
    ],
)
@pytest.mark.parametrize(
    ("of_type", "wrap"),
    [
        pytest.param(Command, lambda command: command, id="command"),
        pytest.param(list[Command], lambda command: [command], id="commands"),
    ],
)
def test_replace_reference_one_argument_of_command(
    example: EnvConfigCreator,
    monkeypatch: pytest.MonkeyPatch,
    value: str,
    config: str,
    expected: str,
    of_type: type[Command | list[Command]],
    wrap: Callable[[Command], Command | list[Command]],
) -> None:
    monkeypatch.delenv("MISSING", raising=False)
    env_config: Final[ConfigSet] = example(config)
    env_config.add_constant(keys="p", desc="p", value=value)
    env_config.add_config(keys="c", of_type=of_type, default=None, desc="c")
    assert env_config["c"] == wrap(Command(args=["python", expected.replace("{}", value), "-x"]))


@pytest.mark.parametrize(
    ("value", "config", "expected"),
    [
        pytest.param(Path("a b"), "{p}", ["a b"], id="path"),
        pytest.param(["a b", Path("c d")], "{p}", ["a b", "c d"], id="list"),
        pytest.param(["a b", Path("c d")], "'{p}'", ["a b c d"], id="list-quoted"),
        pytest.param({"a b"}, "{p}", ["a b"], id="set"),
        pytest.param([], "{p}", [], id="list-empty"),
        pytest.param("", "{p}", [], id="str-empty"),
        pytest.param([Command(["a b", "c"])], "{p}", ["a b", "c"], id="commands"),
    ],
)
def test_replace_reference_arguments_of_command(
    example: EnvConfigCreator,
    value: str | Path | list[str | Path | Command] | set[str],
    config: str,
    expected: list[str],
) -> None:
    env_config: Final[ConfigSet] = example(f"c = python {config} -x")
    env_config.add_constant(keys="p", desc="p", value=value)
    env_config.add_config(keys="c", of_type=list[Command], default=[], desc="c")
    assert env_config["c"] == [Command(args=["python", *expected, "-x"])]


@pytest.mark.parametrize(
    ("source", "suffix"),
    [
        pytest.param("a b", "a b", id="space"),
        pytest.param(r"a\#b", "a#b", id="hash"),
        pytest.param(r"a \#b", "a #b", id="space-and-hash"),
    ],
)
def test_replace_reference_to_path_setting_one_argument_of_command(
    example: EnvConfigCreator, tmp_path: Path, source: str, suffix: str
) -> None:
    env_config: Final[ConfigSet] = example(f"p = {{tox_root}}/{source}\nc = python {{p}}/c -x")
    env_config.add_config(keys="p", of_type=Path, default=Path(), desc="p")
    env_config.add_config(keys="c", of_type=list[Command], default=[], desc="c")
    assert env_config["c"] == [Command(args=["python", f"{tmp_path / 'c' / suffix}/c", "-x"])]


def test_replace_reference_to_str_setting_is_command_text(example: EnvConfigCreator) -> None:
    env_config: Final[ConfigSet] = example("p = -a 'b c'\nc = python {p} -x")
    env_config.add_config(keys="p", of_type=str, default="", desc="p")
    env_config.add_config(keys="c", of_type=list[Command], default=[], desc="c")
    assert env_config["c"] == [Command(args=["python", "-a", "b c", "-x"])]


@pytest.mark.parametrize(
    ("of_type", "expected"),
    [
        pytest.param(str, "k=a 'b/c", id="str"),
        pytest.param(Path, Path("k=a 'b/c"), id="path"),
        pytest.param(list[str], ["k=a 'b/c"], id="list"),
        pytest.param(dict[str, str], {"k": "a 'b/c"}, id="dict"),
    ],
)
def test_replace_reference_as_is_outside_command(
    example: EnvConfigCreator,
    of_type: type[str | Path | list[str] | dict[str, str]],
    expected: str | Path | list[str] | dict[str, str],
) -> None:
    env_config: Final[ConfigSet] = example("o = k={p}/c")
    env_config.add_constant(keys="p", desc="p", value=Path("a 'b"))
    env_config.add_config(keys="o", of_type=of_type, default=None, desc="o")
    assert env_config["o"] == expected


@pytest.mark.parametrize(
    ("config", "section", "content"),
    [
        pytest.param("tox.ini", "testenv:py", "", id="ini"),
        pytest.param("tox.toml", "env.py", "[env_run_base]", id="toml"),
    ],
)
@pytest.mark.parametrize(
    ("key", "wrap"),
    [
        pytest.param("commands", lambda command: [command], id="commands"),
        pytest.param("list_dependencies_command", lambda command: command, id="single-command"),
    ],
)
def test_replace_reference_one_argument_of_command_override(
    tox_project: ToxProjectCreator,
    config: str,
    section: str,
    content: str,
    key: str,
    wrap: Callable[[Command], Command | list[Command]],
) -> None:
    project: Final[ToxProject] = tox_project({config: content})
    override: Final[str] = f"{section}.{key}=python {{work_dir}}{{/}}a -x"
    outcome: Final[ToxRunOutcome] = project.run("c", "-e", "py", "-k", key, "--workdir", "w d", "-x", override)
    outcome.assert_success()
    assert outcome.env_conf("py")[key] == wrap(Command(args=["python", str(project.path / "w d" / "a"), "-x"]))
