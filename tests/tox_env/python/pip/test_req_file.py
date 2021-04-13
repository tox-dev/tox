from pathlib import Path

import pytest

from tox.tox_env.python.pip.req_file import PythonDeps


@pytest.mark.parametrize("legacy_flag", ["-r", "-c"])
def test_legacy_requirement_file(tmp_path: Path, legacy_flag: str) -> None:
    python_deps = PythonDeps(f"{legacy_flag}a.txt", tmp_path)
    (tmp_path / "a.txt").write_text("b")
    assert python_deps.as_root_args == [legacy_flag, "a.txt"]
    assert vars(python_deps.options) == {}
    assert [str(i) for i in python_deps.requirements] == ["b" if legacy_flag == "-r" else "-c b"]
