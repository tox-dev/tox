from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest
import tomli_w

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize(
    ("base", "reference"),
    [
        pytest.param('{MAGIC="base"}', '[{replace="ref", of=["env_run_base", "set_env"]}]', id="table"),
        pytest.param(
            '[{MAGIC="base"}]', '[{replace="ref", of=["env_run_base", "set_env"], extend=true}]', id="extended-list"
        ),
        pytest.param('[{MAGIC="base"}]', '{replace="ref", of=["env_run_base", "set_env"]}', id="whole-list"),
        pytest.param('"MAGIC=base"', '{replace="ref", of=["env_run_base", "set_env"]}', id="whole-string"),
    ],
)
def test_set_env_override_native_toml_reference_runs(tox_project: ToxProjectCreator, base: str, reference: str) -> None:
    result = tox_project({
        "tox.toml": f'[env_run_base]\nset_env={base}\n[env.py]\npackage="skip"\nset_env={reference}\n'
        'commands=[["python", "-c", "import os; print(os.environ[\\"MAGIC\\"])"]]\n'
    }).run("r", "-e", "py", "-x", "env_run_base.set_env+=MAGIC=native")
    result.assert_success()
    assert "native" in result.out.splitlines()


@pytest.mark.parametrize(
    ("filename", "config", "namespace"),
    [
        pytest.param(
            "tox.toml",
            '[env_run_base]\nset_env={file="{env:FILE}"}\n[env.py]\n'
            'package="skip"\nset_env=[{replace="ref", of=["env_run_base", "set_env"]}, {FILE="child.env"}]\n'
            'commands=[["python", "-c", "import os; print(os.environ[\\"MAGIC\\"])"]]\n',
            "env_run_base",
            id="toml",
        ),
        pytest.param(
            "tox.ini",
            "[testenv]\nset_env=file|{env:FILE}\n[testenv:py]\npackage=skip\n"
            "set_env=\n {[testenv]set_env}\n FILE=child.env\n"
            """commands=python -c "import os; print(os.environ['MAGIC'])"\n""",
            "testenv",
            id="ini",
        ),
    ],
)
@pytest.mark.parametrize("override", [pytest.param(False, id="config"), pytest.param(True, id="override")])
def test_set_env_native_reference_file_selector_runs(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    config: str,
    namespace: str,
    override: bool,
) -> None:
    monkeypatch.setenv("FILE", "host.env")
    flags = ["-x", f"{namespace}.set_env+=ADDED=yes"] if override else []
    result = tox_project({filename: config, "host.env": "MAGIC=host", "child.env": "MAGIC=child"}).run(
        "r", "-e", "py", *flags
    )
    result.assert_success()
    assert "child" in result.out.splitlines()


@pytest.mark.parametrize(
    ("base", "extend"),
    [
        pytest.param('[{MAGIC="base"}]', False, id="nested-list-needs-extend"),
        pytest.param('{MAGIC="base"}', True, id="table-cannot-extend"),
        pytest.param('"MAGIC=base"', False, id="string-cannot-be-table"),
    ],
)
def test_set_env_override_native_toml_rejects_wrong_shape(
    tox_project: ToxProjectCreator, base: str, extend: bool
) -> None:
    result = tox_project({
        "tox.toml": f'[env_run_base]\nset_env={base}\n[env.py]\npackage="skip"\n'
        f'set_env=[{{replace="ref", of=["env_run_base", "set_env"], extend={str(extend).lower()}}}]\n'
    }).run("r", "-e", "py", "-x", "env_run_base.set_env+=MAGIC=native")
    result.assert_failed(code=1)
    assert "set_env arrays require table references or array references with extend=true" in result.out


def test_set_env_native_toml_keeps_literal_values(tox_project: ToxProjectCreator) -> None:
    value: Final = "  café;#\nsecond line  "
    result = tox_project({
        "tox.toml": tomli_w.dumps({
            "env_run_base": {"set_env": [{"MAGIC": value}]},
            "env": {
                "py": {
                    "package": "skip",
                    "set_env": [{"replace": "ref", "of": ["env_run_base", "set_env"], "extend": True}],
                    "commands": [["python", "-c", "import os; print(repr(os.environ['MAGIC']))"]],
                }
            },
        })
    }).run("r", "-e", "py", "-x", "env_run_base.set_env+=ADDED=yes")
    result.assert_success()
    assert repr(value) in result.out.splitlines()


@pytest.mark.parametrize("reference", [pytest.param(False, id="inline"), pytest.param(True, id="reference")])
@pytest.mark.parametrize(
    "direct", [pytest.param(False, id="file-only"), pytest.param(True, id="file-overrides-direct")]
)
def test_set_env_native_toml_file_selector_from_previous_file(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch, reference: bool, direct: bool
) -> None:
    monkeypatch.setenv("FILE", "host.env")
    first = (
        '{replace="ref", of=["env_run_base", "set_env"], extend=true}'
        if reference and direct
        else '{replace="ref", of=["env_run_base", "set_env"]}'
        if reference
        else '{file="selector.env"}'
    )
    result = tox_project({
        "tox.toml": "[env_run_base]\nset_env="
        + ('[{FILE="host.env"}, {file="selector.env"}]' if direct else '{file="selector.env"}')
        + '\n[env.py]\npackage="skip"\n'
        f'set_env=[{first}, {{file="{{env:FILE}}"}}]\n'
        'commands=[["python", "-c", "import os; print(os.environ[\\"MAGIC\\"])"]]\n',
        "selector.env": "FILE=child.env",
        "host.env": "MAGIC=host",
        "child.env": "MAGIC=child",
    }).run("r", "-e", "py", "-x", "env_run_base.set_env+=ADDED=yes")
    result.assert_success()
    assert "child" in result.out.splitlines()


@pytest.mark.parametrize("filename", [pytest.param("tox.ini", id="ini"), pytest.param("tox.toml", id="toml")])
def test_set_env_override_file_selector_from_previous_override(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch, filename: str
) -> None:
    monkeypatch.setenv("FILE", "host.env")
    config = (
        "[testenv]\npackage=skip\nset_env=\ncommands=python -c \"import os; print(os.environ['MAGIC'])\"\n"
        if filename == "tox.ini"
        else '[env_run_base]\npackage="skip"\nset_env={}\n'
        'commands=[["python", "-c", "import os; print(os.environ[\\"MAGIC\\"])"]]\n'
    )
    namespace = "testenv" if filename == "tox.ini" else "env_run_base"
    result = tox_project({
        filename: config,
        "selector.env": "FILE=child.env",
        "host.env": "MAGIC=host",
        "child.env": "MAGIC=child",
    }).run(
        "r",
        "-e",
        "py",
        "-x",
        f"{namespace}.set_env+=file|selector.env",
        "-x",
        f"{namespace}.set_env+=file|{{env:FILE}}",
    )
    result.assert_success()
    assert "child" in result.out.splitlines()


@pytest.mark.parametrize(
    ("filename", "config"),
    [
        pytest.param("tox.ini", "[testenv]\npackage=skip\nset_env=file|broken.env\n", id="ini"),
        pytest.param("tox.toml", '[env_run_base]\npackage="skip"\nset_env={file="broken.env"}\n', id="toml"),
    ],
)
def test_set_env_native_rejects_invalid_env_file(tox_project: ToxProjectCreator, filename: str, config: str) -> None:
    result = tox_project({filename: config, "broken.env": "MISSING_SEPARATOR"}).run("r", "-e", "py")
    result.assert_failed(code=1)
    assert "invalid line 'MISSING_SEPARATOR' in set_env" in result.out
