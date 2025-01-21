from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import MonkeyPatch, ToxProjectCreator


def test_show_schema_empty_dir(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    project = tox_project({})
    result = project.run("-qq", "schema")
    schema = json.loads(result.out)
    assert "properties" in schema
    assert "tox_root" in schema["properties"]
