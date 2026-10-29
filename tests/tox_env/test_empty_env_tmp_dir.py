from __future__ import annotations

import os
import subprocess
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import pytest


@pytest.mark.integration
def test_unset_env_tmp_dir_does_not_clear_the_project(tmp_path: Path) -> None:
    var = "TOX_TEST_NO_SUCH_VARIABLE_FOR_ENV_TMP_DIR"
    (tmp_path / "tox.ini").write_text(
        f"[testenv]\nenv_tmp_dir = {{env:{var}}}\npackage = skip\ncommands = python -c \"print('ok')\"\n",
        encoding="utf-8",
    )
    (tmp_path / "keep.txt").write_text("keep\n", encoding="utf-8")
    env = {name: value for name, value in os.environ.items() if name != var}
    result = subprocess.run(
        [sys.executable, "-m", "tox", "r", "-e", "py"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode != 0, output
    assert "refusing to clear it" in output, output
    assert (tmp_path / "keep.txt").exists(), "the project directory must be left alone"
    assert (tmp_path / "tox.ini").exists()
