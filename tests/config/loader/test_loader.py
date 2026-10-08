from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.config.cli.parse import get_options
from tox.config.loader.api import Override, apply_overrides_to_raw

if TYPE_CHECKING:
    from tox.pytest import CaptureFixture, ToxProjectCreator


@pytest.mark.parametrize("flag", ["-x", "--override"])
def test_override_incorrect(flag: str, capsys: CaptureFixture) -> None:
    with pytest.raises(SystemExit):
        get_options(flag, "magic")
    out, err = capsys.readouterr()
    assert not out
    assert "override magic has no = sign in it" in err


@pytest.mark.parametrize("flag", ["-x", "--override"])
def test_override_add(flag: str) -> None:
    parsed, _, __, ___, ____ = get_options(flag, "magic=true")
    assert len(parsed.override) == 1
    value = parsed.override[0]
    assert value.key == "magic"
    assert value.value == "true"
    assert not value.namespace
    assert value.append is False


@pytest.mark.parametrize("flag", ["-x", "--override"])
def test_override_append(flag: str) -> None:
    parsed, _, __, ___, ____ = get_options(flag, "magic+=true")
    assert len(parsed.override) == 1
    value = parsed.override[0]
    assert value.key == "magic"
    assert value.value == "true"
    assert not value.namespace
    assert value.append is True


@pytest.mark.parametrize("flag", ["-x", "--override"])
def test_override_multiple(flag: str) -> None:
    parsed, _, __, ___, ____ = get_options(flag, "magic+=1", flag, "magic+=2")
    assert len(parsed.override) == 2


def test_override_equals() -> None:
    assert Override("a=b") == Override("a=b")


def test_override_not_equals() -> None:
    assert Override("a=b") != Override("c=d")


def test_override_not_equals_different_type() -> None:
    assert Override("a=b") != 1


def test_override_repr() -> None:
    assert repr(Override("b.a=c")) == "Override('b.a=c')"


@pytest.mark.parametrize(
    ("raw", "namespace", "key", "value", "append", "expected_str"),
    [
        pytest.param("env.3\\.14.deps=foo", "env.3.14", "deps", "foo", False, "env.3\\.14.deps=foo", id="escaped_dot"),
        pytest.param("a\\.b\\.c.key=val", "a.b.c", "key", "val", False, "a\\.b\\.c.key=val", id="multiple_escaped"),
        pytest.param(
            "env.3\\.14.deps+=bar", "env.3.14", "deps", "bar", True, "env.3\\.14.deps+=bar", id="escaped_append"
        ),
        pytest.param("testenv.deps=foo", "testenv", "deps", "foo", False, "testenv.deps=foo", id="no_escape_compat"),
        pytest.param(
            "test\\env.key=val", "test\\env", "key", "val", False, "test\\env.key=val", id="backslash_not_before_dot"
        ),
    ],
)
def test_override_escaped_dot(raw: str, namespace: str, key: str, value: str, append: bool, expected_str: str) -> None:
    override = Override(raw)
    assert override.namespace == namespace
    assert override.key == key
    assert override.value == value
    assert override.append is append
    assert str(override) == expected_str


@pytest.mark.parametrize(
    ("override", "raw", "expected"),
    [
        pytest.param("ns.k=blue", ["red"], ["blue"], id="list-replace"),
        pytest.param("ns.k+=blue", ["red"], ["red", "blue"], id="list-append"),
        pytest.param("ns.k=blue", "red", "blue", id="scalar-replace"),
        pytest.param("ns.k+=blue", "red", "red\nblue", id="str-append"),
        pytest.param("ns.k=a=1", {"b": "2"}, {"a": "1"}, id="dict-replace"),
        pytest.param("ns.k+=a=1", {"b": "2"}, {"b": "2", "a": "1"}, id="dict-append"),
    ],
)
def test_apply_overrides_to_raw(override: str, raw: object, expected: object) -> None:
    assert apply_overrides_to_raw([Override(override)], "k", raw) == expected


def test_apply_overrides_to_raw_ignores_other_keys() -> None:
    assert apply_overrides_to_raw([Override("ns.other=blue")], "k", ["red"]) == ["red"]


def test_apply_overrides_to_raw_append_unsupported_type() -> None:
    with pytest.raises(ValueError, match="Only able to append to lists, dicts and strings"):
        apply_overrides_to_raw([Override("ns.k+=1")], "k", 0)


@pytest.mark.parametrize(
    ("filename", "content", "namespace"),
    [
        pytest.param(
            "tox.toml",
            'env_list = ["a"]\n[env_run_base]\nskip_install = true\ncommands = [["python"]]\n',
            "env_run_base",
            id="toml",
        ),
        pytest.param(
            "tox.ini",
            "[tox]\nenv_list = a\n[testenv]\nskip_install = true\ncommands = python\n",
            "testenv",
            id="ini",
        ),
    ],
)
@pytest.mark.parametrize(
    ("override", "posargs", "expected"),
    [
        pytest.param("python {posargs}", ["--", "tests", "src"], "python tests src", id="posargs"),
        pytest.param("python {posargs:tests}", [], "python tests", id="posargs-default"),
        pytest.param("python {env:MAGIC}", [], "python from-env", id="env"),
        pytest.param("python {env_name}", [], "python a", id="env-name"),
    ],
)
def test_override_value_is_substituted(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content: str,
    namespace: str,
    override: str,
    posargs: list[str],
    expected: str,
) -> None:
    monkeypatch.setenv("MAGIC", "from-env")
    project = tox_project({filename: content})
    outcome = project.run("c", "-e", "a", "-k", "commands", "-x", f"{namespace}.commands={override}", *posargs)
    outcome.assert_success()
    outcome.assert_out_err(f"[testenv:a]\ncommands = {expected}\n", "")


@pytest.mark.parametrize(
    ("filename", "content", "namespace"),
    [
        pytest.param(
            "tox.toml",
            'env_list = ["a"]\n[env_run_base]\nset_env = {KEEP = "1", MAGIC = "base"}\n',
            "env_run_base",
            id="toml",
        ),
        pytest.param("tox.ini", "[tox]\nenv_list = a\n[testenv]\nset_env = KEEP=1\n MAGIC=base\n", "testenv", id="ini"),
        pytest.param("tox.toml", 'env_list = ["a"]\n[env_run_base]\n', "env_run_base", id="toml-no-base"),
        pytest.param("tox.ini", "[tox]\nenv_list = a\n[testenv]\n", "testenv", id="ini-no-base"),
    ],
)
@pytest.mark.parametrize(
    ("override", "expected"),
    [
        pytest.param("set_env+=MAGIC={env_name}", ["MAGIC=a"], id="append"),
        pytest.param("set_env=MAGIC={env_name}", ["MAGIC=a"], id="replace"),
        pytest.param("set_env+=MAGIC={env:FROM_SHELL}", ["MAGIC=from-shell"], id="env"),
        pytest.param("set_env+=MAGIC={env:KEEP:1}", ["MAGIC=1"], id="base-reference"),
        pytest.param("set_env+=file|{env_name}.env", ["MAGIC=from-file"], id="file"),
        pytest.param("set_env+=MAGIC={env_name}; sys_platform == 'nope'", [], id="marker"),
    ],
)
def test_override_set_env_value_is_substituted(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content: str,
    namespace: str,
    override: str,
    expected: list[str],
) -> None:
    monkeypatch.setenv("FROM_SHELL", "from-shell")
    project = tox_project({filename: content, "a.env": "MAGIC=from-file"})
    outcome = project.run("c", "-e", "a", "-k", "set_env", "-x", f"{namespace}.{override}")
    outcome.assert_success()
    assert [line.strip() for line in outcome.out.splitlines() if line.strip().startswith(("KEEP=", "MAGIC="))] == [
        *(["KEEP=1"] if "KEEP" in content and override.startswith("set_env+=") else []),
        *expected,
    ]


@pytest.mark.parametrize(
    ("filename", "content", "namespace"),
    [
        pytest.param("tox.ini", "[tox]\nenv_list = a\n[testenv]\nset_env = MAGIC=base\n", "testenv", id="ini"),
        pytest.param(
            "tox.toml", 'env_list = ["a"]\n[env_run_base]\nset_env.MAGIC = "base"\n', "env_run_base", id="toml"
        ),
    ],
)
@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param(["{env:BLOCK}"], ["MAGIC=a", "NEW=a"], id="block-over-base"),
        pytest.param(["{env:BLOCK}", "MAGIC=later"], ["MAGIC=later", "NEW=later"], id="later-direct-key"),
        pytest.param(["MAGIC=earlier", "{env:BLOCK}"], ["MAGIC=a", "NEW=a"], id="block-over-earlier-override"),
        pytest.param(["{env:BLOCK}", "{env:SECOND_BLOCK}"], ["MAGIC=second", "NEW=second"], id="later-block"),
        pytest.param(["{env:BLOCK}\nMAGIC=local"], ["MAGIC=local", "NEW=local"], id="direct-key-within-block"),
        pytest.param(["{env:DISABLED_BLOCK}"], ["NEW="], id="false-marker-within-block"),
        pytest.param(["{env:BLOCK}", "file|a.env"], ["MAGIC=file", "NEW=file"], id="later-file"),
        pytest.param(["file|a.env", "{env:BLOCK}"], ["MAGIC=a", "NEW=a"], id="block-over-file"),
    ],
)
@pytest.mark.parametrize("channel", [pytest.param("cli", id="cli"), pytest.param("env", id="tox-override")])
def test_override_set_env_block_precedence(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content: str,
    namespace: str,
    overrides: list[str],
    expected: list[str],
    channel: str,
) -> None:
    monkeypatch.delenv("MAGIC", raising=False)
    monkeypatch.setenv("BLOCK", "MAGIC={env_name}\nNEW={env:MAGIC}")
    monkeypatch.setenv("SECOND_BLOCK", "MAGIC=second\nNEW={env:MAGIC}")
    project = tox_project({filename: content, "a.env": "MAGIC=file"})
    monkeypatch.setenv("DISABLED_BLOCK", "MAGIC=disabled; sys_platform == 'nope'\nNEW={env:MAGIC}")
    values = [f"{namespace}.set_env+={value}" for value in overrides]
    if channel == "env":
        monkeypatch.setenv("TOX_OVERRIDE", ";".join(values))
    flags = [item for value in values for item in ("-x", value)] if channel == "cli" else []
    outcome = project.run("c", "-e", "a", "-k", "set_env", *flags)
    outcome.assert_success()
    assert [
        line.strip() for line in outcome.out.splitlines() if line.strip().startswith(("MAGIC=", "NEW="))
    ] == expected


@pytest.mark.parametrize(
    ("files", "args"),
    [
        pytest.param({"tox.ini": "[testenv]\nskip_install = maybe"}, ("r",), id="ini-run"),
        pytest.param({"tox.ini": "[testenv]\nskip_install = maybe"}, ("c", "-k", "skip_install"), id="ini-config"),
        pytest.param(
            {"tox.toml": "[env_run_base]\nskip_install = true"},
            ("r", "-x", "env_run_base.skip_install=maybe"),
            id="override",
        ),
    ],
)
def test_bad_value_is_handled_error(
    tox_project: ToxProjectCreator, files: dict[str, str], args: tuple[str, ...]
) -> None:
    outcome = tox_project(files).run(*args, "-e", "py")
    outcome.assert_failed(code=-2)
    assert "HandledError| failed to load py.skip_install: value 'maybe' cannot be transformed to bool" in outcome.out
