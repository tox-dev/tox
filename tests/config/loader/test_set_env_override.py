from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize(
    ("block", "files", "expected"),
    [
        pytest.param(
            "file|{env:TOX_ENV_NAME}.env",
            {"a.env": "TOX_ENV_NAME=wrong\nMAGIC={env:TOX_ENV_NAME}"},
            ["MAGIC=a", "TOX_ENV_NAME=a"],
            id="exported-filename",
        ),
        pytest.param(
            "TOX_ENV_NAME=wrong\nMAGIC={env:TOX_ENV_NAME}", {}, ["MAGIC=a", "TOX_ENV_NAME=a"], id="exported-inline"
        ),
    ],
)
def test_set_env_override_preserves_exports(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    block: str,
    files: dict[str, str],
    expected: list[str],
) -> None:
    monkeypatch.setenv("BLOCK", block)
    result = tox_project({"tox.ini": "[tox]\nenv_list=a\n[testenv]\npackage=skip\n", **files}).run(
        "c", "-e", "a", "-k", "set_env", "-x", "testenv.set_env+={env:BLOCK}"
    )
    result.assert_success()
    assert [
        line.strip() for line in result.out.splitlines() if line.strip().startswith(("MAGIC=", "TOX_ENV_NAME="))
    ] == expected


_PROPAGATES_FILES: Final = pytest.mark.parametrize(
    ("filename", "config", "namespace"),
    [
        pytest.param(
            "tox.ini",
            "[tox]\nenv_list=a\n[testenv]\nset_env=MAGIC=base\n[testenv:a]\nset_env={[testenv]set_env}\n",
            "testenv",
            id="ini",
        ),
        pytest.param(
            "tox.toml",
            'env_list=["a"]\n[env_run_base]\nset_env.MAGIC="base"\n[env.a]\n'
            'set_env={replace="ref", of=["env_run_base", "set_env"]}\n',
            "env_run_base",
            id="toml",
        ),
    ],
)
_PROPAGATES_OVERRIDES: Final = pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param(["set_env+={env:BLOCK}"], ["MAGIC=a", "NEW=a"], id="append-block"),
        pytest.param(["set_env={env:BLOCK}"], ["MAGIC=a", "NEW=a"], id="replace-block"),
        pytest.param(
            ["set_env=MAGIC=reset", "set_env+={env:BLOCK}", "set_env+=MAGIC=later"],
            ["MAGIC=later", "NEW=later"],
            id="reset-then-append",
        ),
        pytest.param(["set_env+=MAGIC={env:MAGIC}"], ["MAGIC=from-shell"], id="self-reference"),
        pytest.param(["set_env+=MAGIC={posargs:{env_name}}"], ["MAGIC=a"], id="posargs-default"),
        pytest.param(["set_env+={env:DISABLED}"], ["NEW=from-shell"], id="false-marker"),
        pytest.param(["set_env+={env:ENABLED}"], ["MAGIC=enabled;literal", "NEW=enabled;literal"], id="true-marker"),
        pytest.param(["set_env+=file|{env_name}.env"], ["MAGIC=café;literal", "NEW=café;literal"], id="env-file"),
    ],
)


@_PROPAGATES_FILES
@_PROPAGATES_OVERRIDES
@pytest.mark.parametrize("key", [pytest.param("set_env", id="canonical"), pytest.param("setenv", id="alias")])
def test_set_env_override_propagates_through_reference_cli(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    config: str,
    namespace: str,
    overrides: list[str],
    expected: list[str],
    key: str,
) -> None:
    monkeypatch.setenv("MAGIC", "from-shell")
    monkeypatch.setenv("BLOCK", "MAGIC={env_name}\nNEW={env:MAGIC}")
    monkeypatch.setenv("DISABLED", "MAGIC=disabled; sys_platform == 'nope'\nNEW={env:MAGIC}")
    monkeypatch.setenv("ENABLED", r"MAGIC=enabled\;literal; sys_platform != 'nope'" + "\nNEW={env:MAGIC}")
    values = [f"{namespace}.{value.replace('set_env', key, 1)}" for value in overrides]
    result = tox_project({filename: config, "a.env": "MAGIC=café;literal\nNEW={env:MAGIC}"}).run(
        "c", "-e", "a", "-k", "set_env", *[item for value in values for item in ("-x", value)]
    )
    result.assert_success()
    assert [line.strip() for line in result.out.splitlines() if line.strip().startswith(("MAGIC=", "NEW="))] == expected


@_PROPAGATES_FILES
@_PROPAGATES_OVERRIDES
@pytest.mark.parametrize("key", [pytest.param("set_env", id="canonical"), pytest.param("setenv", id="alias")])
def test_set_env_override_propagates_through_reference_tox_override(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    config: str,
    namespace: str,
    overrides: list[str],
    expected: list[str],
    key: str,
) -> None:
    monkeypatch.setenv("MAGIC", "from-shell")
    monkeypatch.setenv("BLOCK", "MAGIC={env_name}\nNEW={env:MAGIC}")
    monkeypatch.setenv("DISABLED", "MAGIC=disabled; sys_platform == 'nope'\nNEW={env:MAGIC}")
    monkeypatch.setenv("ENABLED", r"MAGIC=enabled\;literal; sys_platform != 'nope'" + "\nNEW={env:MAGIC}")
    values = [f"{namespace}.{value.replace('set_env', key, 1)}" for value in overrides]
    monkeypatch.setenv("TOX_OVERRIDE", ";".join(values))
    result = tox_project({filename: config, "a.env": "MAGIC=café;literal\nNEW={env:MAGIC}"}).run(
        "c",
        "-e",
        "a",
        "-k",
        "set_env",
    )
    result.assert_success()
    assert [line.strip() for line in result.out.splitlines() if line.strip().startswith(("MAGIC=", "NEW="))] == expected


@pytest.mark.parametrize(
    ("filename", "config", "namespace"),
    [
        pytest.param("tox.ini", "[testenv]\npackage=skip\nset_env={[testenv]set_env}\n", "testenv", id="ini"),
        pytest.param(
            "tox.toml",
            '[env_run_base]\npackage="skip"\nset_env={replace="ref", of=["env_run_base", "set_env"]}\n',
            "env_run_base",
            id="toml",
        ),
    ],
)
def test_set_env_override_reference_cycle_fails(
    tox_project: ToxProjectCreator, filename: str, config: str, namespace: str
) -> None:
    result = tox_project({filename: config}).run("r", "-e", "py", "-x", f"{namespace}.set_env+=MAGIC=value")
    result.assert_failed(code=1)
    assert "circular set_env reference" in result.out


_CHILD_KEYS_INI: Final = "[testenv]\nset_env=MAGIC=base\n[testenv:py]\nset_env=\n {[testenv]set_env}\n MAGIC=child\n"
_CHILD_KEYS_TOML: Final = (
    '[env_run_base]\nset_env.MAGIC="base"\n[env.py]\n'
    'set_env=[{replace="ref", of=["env_run_base", "set_env"]}, {MAGIC="child"}]\n'
)


@pytest.mark.parametrize(
    ("filename", "config", "namespace", "flags", "value"),
    [
        pytest.param("tox.ini", _CHILD_KEYS_INI, "testenv", [], "child", id="ini"),
        pytest.param("tox.toml", _CHILD_KEYS_TOML, "env_run_base", [], "child", id="toml"),
        pytest.param(
            "tox.ini",
            _CHILD_KEYS_INI,
            "testenv",
            ["-x", "testenv:py.set_env+=MAGIC=cli"],
            "cli",
            id="ini-child-override",
        ),
        pytest.param(
            "tox.toml",
            _CHILD_KEYS_TOML,
            "env_run_base",
            ["-x", "env.py.set_env+=MAGIC=cli"],
            "cli",
            id="toml-child-override",
        ),
    ],
)
def test_set_env_override_reference_preserves_child_keys(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    config: str,
    namespace: str,
    flags: list[str],
    value: str,
) -> None:
    monkeypatch.setenv("BLOCK", "MAGIC=override; sys_platform == 'nope'\nNEW={env:MAGIC}")
    result = tox_project({filename: config}).run(
        "c", "-e", "py", "-k", "set_env", "-x", f"{namespace}.set_env+={{env:BLOCK}}", *flags
    )
    result.assert_success()
    assert [line.strip() for line in result.out.splitlines() if line.strip().startswith(("MAGIC=", "NEW="))] == [
        f"MAGIC={value}",
        f"NEW={value}",
    ]


@pytest.mark.parametrize(
    ("filename", "config", "namespace"),
    [
        pytest.param(
            "tox.ini",
            "[testenv]\nset_env=file|base.env\n[testenv:py]\nset_env={[testenv]set_env}\n",
            "testenv",
            id="ini",
        ),
        pytest.param(
            "tox.toml",
            '[env_run_base]\nset_env=[{file="base.env"}, {file="other.env"}]\n[env.py]\n'
            'set_env={replace="ref", of=["env_run_base", "set_env"]}\n',
            "env_run_base",
            id="toml",
        ),
    ],
)
def test_set_env_override_reference_preserves_env_file_keys(
    tox_project: ToxProjectCreator, filename: str, config: str, namespace: str
) -> None:
    result = tox_project({
        filename: config,
        "base.env": "file=literal\nMAGIC=base",
        "other.env": "MAGIC=second",
        "last.env": "MAGIC=last\nNEW={env:file}",
    }).run("c", "-e", "py", "-k", "set_env", "-x", f"{namespace}.set_env+=file|last.env")
    result.assert_success()
    assert [
        line.strip() for line in result.out.splitlines() if line.strip().startswith(("file=", "MAGIC=", "NEW="))
    ] == ["MAGIC=last", "NEW=literal", "file=literal"]


def test_set_env_override_reference_uses_child_selector(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BLOCK", "MAGIC=from-shell")
    result = tox_project({
        "tox.toml": '[env_run_base]\nset_env.MAGIC="base"\n[env.py]\n'
        'set_env=[{replace="ref", of=["env_run_base", "set_env"]}, {BLOCK="MAGIC=child"}]\n'
    }).run("c", "-e", "py", "-k", "set_env", "-x", "env_run_base.set_env+={env:BLOCK}")
    result.assert_success()
    assert "MAGIC=child" in [line.strip() for line in result.out.splitlines()]


def test_set_env_override_reference_preserves_child_file_order(tox_project: ToxProjectCreator) -> None:
    result = tox_project({
        "tox.toml": '[env_run_base]\nset_env.MAGIC="base"\n[env.py]\n'
        'set_env=[{file="before.env"}, {replace="ref", of=["env_run_base", "set_env"]},'
        '{file="after.env"}, {MAGIC="last"}]\n',
        "before.env": "FIRST=first\nMAGIC=first",
        "after.env": "MAGIC=after\nLAST=last",
    }).run("c", "-e", "py", "-k", "set_env", "-x", "env_run_base.set_env+=MAGIC=override")
    result.assert_success()
    assert [
        line.strip() for line in result.out.splitlines() if line.strip().startswith(("FIRST=", "LAST=", "MAGIC="))
    ] == ["FIRST=first", "LAST=last", "MAGIC=last"]


def test_set_env_override_reference_appends_to_filtered_base(tox_project: ToxProjectCreator) -> None:
    result = tox_project({
        "tox.ini": "[testenv]\nset_env=win: MAGIC=base\n[testenv:py]\nset_env={[testenv]set_env}\n"
    }).run("c", "-e", "py", "-k", "set_env", "-x", "testenv.set_env+=MAGIC=appended")
    result.assert_success()
    assert "MAGIC=appended" in [line.strip() for line in result.out.splitlines()]
