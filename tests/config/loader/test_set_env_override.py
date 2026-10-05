from __future__ import annotations

from typing import TYPE_CHECKING

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


@pytest.mark.parametrize(
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
@pytest.mark.parametrize(
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
@pytest.mark.parametrize("channel", [pytest.param("cli", id="cli"), pytest.param("env", id="tox-override")])
@pytest.mark.parametrize("key", [pytest.param("set_env", id="canonical"), pytest.param("setenv", id="alias")])
def test_set_env_override_propagates_through_reference(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    config: str,
    namespace: str,
    overrides: list[str],
    expected: list[str],
    channel: str,
    key: str,
) -> None:
    monkeypatch.setenv("MAGIC", "from-shell")
    monkeypatch.setenv("BLOCK", "MAGIC={env_name}\nNEW={env:MAGIC}")
    monkeypatch.setenv("DISABLED", "MAGIC=disabled; sys_platform == 'nope'\nNEW={env:MAGIC}")
    monkeypatch.setenv("ENABLED", r"MAGIC=enabled\;literal; sys_platform != 'nope'" + "\nNEW={env:MAGIC}")
    values = [f"{namespace}.{value.replace('set_env', key, 1)}" for value in overrides]
    if channel == "env":
        monkeypatch.setenv("TOX_OVERRIDE", ";".join(values))
    flags = [item for value in values for item in ("-x", value)] if channel == "cli" else []
    result = tox_project({filename: config, "a.env": "MAGIC=café;literal\nNEW={env:MAGIC}"}).run(
        "c", "-e", "a", "-k", "set_env", *flags
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


@pytest.mark.parametrize(
    ("filename", "config", "namespace"),
    [
        pytest.param(
            "tox.ini",
            "[testenv]\nset_env=MAGIC=base\n[testenv:py]\nset_env=\n {[testenv]set_env}\n MAGIC=child\n",
            "testenv",
            id="ini",
        ),
        pytest.param(
            "tox.toml",
            '[env_run_base]\nset_env.MAGIC="base"\n[env.py]\n'
            'set_env=[{replace="ref", of=["env_run_base", "set_env"]}, {MAGIC="child"}]\n',
            "env_run_base",
            id="toml",
        ),
    ],
)
@pytest.mark.parametrize("child_override", [pytest.param(False, id="config"), pytest.param(True, id="override")])
def test_set_env_override_reference_preserves_child_keys(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    config: str,
    namespace: str,
    child_override: bool,
) -> None:
    monkeypatch.setenv("BLOCK", "MAGIC=override; sys_platform == 'nope'\nNEW={env:MAGIC}")
    child_namespace = "testenv:py" if filename == "tox.ini" else "env.py"
    flags = ["-x", f"{child_namespace}.set_env+=MAGIC=cli"] if child_override else []
    result = tox_project({filename: config}).run(
        "c", "-e", "py", "-k", "set_env", "-x", f"{namespace}.set_env+={{env:BLOCK}}", *flags
    )
    result.assert_success()
    value = "cli" if child_override else "child"
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
