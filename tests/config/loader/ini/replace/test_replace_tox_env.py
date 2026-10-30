from __future__ import annotations

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
    from tox.pytest import LogCaptureFixture

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


def test_replace_command_circular_fan_out_keeps_following_token(
    load_commands: Callable[[str], list[list[str]]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAGIC", "{env:MAGIC}" * 2)
    monkeypatch.setenv("NEXT", "expanded")
    commands: Final[list[list[str]]] = load_commands("{env:MAGIC} {env:NEXT}")

    assert commands[0][-1] == "{env:NEXT}"


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
    env_config: Final[ConfigSet] = example("items = {env:MAGIC}")
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
