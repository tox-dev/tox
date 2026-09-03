from __future__ import annotations

from typing import TYPE_CHECKING

from tox.tox_env.python.dependency_groups import resolve

if TYPE_CHECKING:
    from pathlib import Path


def test_extra_key_not_canonical(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo-pkg"\n'
        '[project.optional-dependencies]\nextra_1 = ["extra-pkg>=1.0"]\n'
        '[dependency-groups]\ntest = ["demo-pkg[extra_1]"]\n',
        encoding="utf-8",
    )

    assert sorted(str(i) for i in resolve(tmp_path, {"test"})) == ["extra-pkg>=1.0"]


def test_project_name_not_canonical(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo-pkg"\n'
        '[project.optional-dependencies]\nextra1 = ["extra-pkg>=1.0"]\n'
        '[dependency-groups]\ntest = ["demo_pkg[extra1]"]\n',
        encoding="utf-8",
    )

    assert sorted(str(i) for i in resolve(tmp_path, {"test"})) == ["extra-pkg>=1.0"]
