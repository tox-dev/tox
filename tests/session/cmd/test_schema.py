from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import MonkeyPatch, ToxProjectCreator

ROOT = Path(__file__).parents[3]
SCHEMA_PATH = ROOT / "src" / "tox" / "tox.schema.json"


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
            "[tool.tox.env_run_base]\ncommands = [['pytest']]\ndeps = 'pytest'\n\n"
            "[tool.tox.env.lint]\ncommands = [['ruff', 'check', '.']]\n",
            id="pyproject.toml",
        ),
    ],
)
def test_schema_tombi_lint(tmp_path: Path, filename: str, tombi_cfg: str, content: str) -> None:
    if not (tombi := shutil.which("tombi")):
        pytest.skip("tombi not installed")
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
