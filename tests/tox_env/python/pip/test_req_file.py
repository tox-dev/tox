from __future__ import annotations

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


def test_deps_with_hash(tmp_path: Path) -> None:
    """deps with --hash should raise an exception."""
    python_deps = PythonDeps(
        raw="foo==1 --hash sha256:97a702083b0d906517b79672d8501eee470d60ae55df0fa9d4cfba56c7f65a82",
        root=tmp_path,
    )
    with pytest.raises(ValueError, match="Cannot use --hash in deps list"):
        _ = python_deps.requirements


def test_deps_with_requirements_with_hash(tmp_path: Path) -> None:
    """deps can point to a requirements file that has --hash."""
    exp_hash = "sha256:97a702083b0d906517b79672d8501eee470d60ae55df0fa9d4cfba56c7f65a82"
    requirements = tmp_path / "requirements.txt"
    requirements.write_text(f"foo==1 --hash {exp_hash}")
    python_deps = PythonDeps(raw="-r requirements.txt", root=tmp_path)
    assert len(python_deps.requirements) == 1
    parsed_req = python_deps.requirements[0]
    assert str(parsed_req.requirement) == "foo==1"
    assert parsed_req.options == {"hash": [exp_hash]}
    assert parsed_req.from_file == str(requirements)
