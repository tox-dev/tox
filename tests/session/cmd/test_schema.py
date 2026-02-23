from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import MonkeyPatch, ToxProjectCreator

SCHEMA_PATH = Path(__file__).parents[3] / "src" / "tox" / "tox.schema.json"


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
