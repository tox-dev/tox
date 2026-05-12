from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import MonkeyPatch, ToxProjectCreator

ROOT = Path(__file__).parents[3]
SCHEMA_PATH = ROOT / "src" / "tox" / "tox.schema.json"
REPLACE_PY = ROOT / "src" / "tox" / "config" / "loader" / "toml" / "_replace.py"


def test_show_schema_empty_dir(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    project = tox_project({})
    result = project.run("-qq", "schema")
    schema = json.loads(result.out)
    assert "properties" in schema
    assert "tox_root" in schema["properties"]


def test_schema_freshness(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    project = tox_project({
        "tox.toml": 'env_list = ["py"]',
        "pyproject.toml": '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"',
    })
    result = project.run("-qq", "schema")
    generated = json.loads(result.out)
    committed = json.loads(SCHEMA_PATH.read_text())
    assert generated == committed, (
        "tox.schema.json is out of date — regenerate with: tox schema > src/tox/tox.schema.json"
    )


def test_schema_allows_deps_array() -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    deps_schema = schema["properties"]["env_run_base"]["properties"]["deps"]

    assert {"type": "string"} in deps_schema["oneOf"]
    assert {"type": "array", "items": {"$ref": "#/definitions/subs"}} in deps_schema["oneOf"]


@pytest.mark.parametrize(
    ("filename", "tombi_cfg", "content"),
    [
        pytest.param(
            "tox.toml",
            '[[schemas]]\npath = "tox.schema.json"\ninclude = ["tox.toml"]\n',
            (ROOT / "tox.toml").read_text(),
            id="tox.toml",
        ),
        pytest.param(
            "pyproject.toml",
            '[[schemas]]\nroot = "tool.tox"\npath = "tox.schema.json"\ninclude = ["pyproject.toml"]\n',
            "[tool.tox]\nrequires = ['tox>=4']\nenv_list = ['py']\nskip_missing_interpreters = true\n\n"
            "[tool.tox.env_run_base]\ncommands = [['pytest']]\ndeps = ['pytest', '-r requirements.txt']\n\n"
            "[tool.tox.env.lint]\ncommands = [['ruff', 'check', '.']]\n",
            id="pyproject.toml",
        ),
    ],
)
def test_schema_tombi_lint(tmp_path: Path, filename: str, tombi_cfg: str, content: str) -> None:
    tombi = shutil.which("tombi")
    assert tombi is not None, "tombi must be installed (declared in the test extra)"
    shutil.copy2(SCHEMA_PATH, tmp_path / "tox.schema.json")
    (tmp_path / filename).write_text(content)
    (tmp_path / "tombi.toml").write_text(tombi_cfg)
    result = subprocess.run(
        [tombi, "lint", "--error-on-warnings", "--offline", filename],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"


REPLACE_FORM_TOMLS: dict[str, str] = {
    "env": dedent("""
        [env_run_base]
        deps = [{ replace = "env", name = "DEPS_PIN", default = "pytest" }]
    """),
    "ref": dedent("""
        [env_run_base]
        deps = [{ replace = "ref", of = ["env_run_base", "deps"] }]
    """),
    "posargs": dedent("""
        [env_run_base]
        commands = [["pytest", { replace = "posargs", default = ["tests"] }]]
    """),
    "glob": dedent("""
        [env_run_base]
        deps = [{ replace = "glob", pattern = "requirements*.txt", extend = true }]
    """),
    "if": dedent("""
        [env_run_base]
        commands = [
          { replace = "if", condition = "env.CI", then = [["ruff", "check"]], extend = true },
          ["pytest"],
        ]
    """),
}


def _discover_replace_types() -> set[str]:
    """Return the set of replace_type tokens implemented in `_replace.py`."""
    return set(re.findall(r'replace_type == "([a-z]+)"', REPLACE_PY.read_text()))


def test_schema_covers_every_replace_type() -> None:
    """Guard: every `replace_type == "..."` in _replace.py needs a schema variant.

    This catches the failure mode behind issue #3939, where a new replace form (`if`) was added to the loader but never
    wired into the JSON schema.

    """
    implemented = _discover_replace_types()
    schema = json.loads(SCHEMA_PATH.read_text())
    in_schema = {name.removeprefix("replace_") for name in schema["definitions"] if name.startswith("replace_")} - {
        "object"
    }
    assert implemented == in_schema, (
        f"replace types in loader {implemented} differ from schema definitions {in_schema}; "
        f"update src/tox/session/cmd/schema.py and regenerate tox.schema.json"
    )
    assert implemented == set(REPLACE_FORM_TOMLS), (
        f"replace types in loader {implemented} differ from tombi-lint fixtures {set(REPLACE_FORM_TOMLS)}; "
        f"add a sample to REPLACE_FORM_TOMLS in this file"
    )


@pytest.mark.parametrize("replace_type", sorted(REPLACE_FORM_TOMLS))
def test_schema_tombi_lint_replace_forms(tmp_path: Path, replace_type: str) -> None:
    tombi = shutil.which("tombi")
    assert tombi is not None, "tombi must be installed (declared in the test extra)"
    shutil.copy2(SCHEMA_PATH, tmp_path / "tox.schema.json")
    (tmp_path / "tox.toml").write_text(REPLACE_FORM_TOMLS[replace_type])
    (tmp_path / "tombi.toml").write_text('[[schemas]]\npath = "tox.schema.json"\ninclude = ["tox.toml"]\n')
    result = subprocess.run(
        [tombi, "lint", "--error-on-warnings", "--offline", "tox.toml"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
