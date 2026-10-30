from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest
from virtualenv.info import fs_supports_symlink

from tox.tox_env.info import Info

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_info_repr() -> None:
    at_loc = Path().absolute()
    info_object = Info(at_loc)
    assert repr(info_object) == f"Info(path={at_loc / '.tox-info.json'})"


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("null", id="null root"),
        pytest.param('["a"]', id="list root"),
        pytest.param('"text"', id="string root"),
    ],
)
def test_info_non_dict_root_self_heals(tmp_path: Path, content: str) -> None:
    (tmp_path / ".tox-info.json").write_text(content)

    with Info(tmp_path).compare({"python": "3.14"}, "ToxEnv") as (eq, old):
        assert (eq, old) == (False, None)

    assert json.loads((tmp_path / ".tox-info.json").read_text()) == {"ToxEnv": {"python": "3.14"}}


def test_info_non_dict_section_self_heals(tmp_path: Path) -> None:
    (tmp_path / ".tox-info.json").write_text('{"PythonRun": "garbage"}')

    with Info(tmp_path).compare(["six"], "PythonRun", "deps") as (eq, old):
        assert (eq, old) == (False, None)

    assert json.loads((tmp_path / ".tox-info.json").read_text()) == {"PythonRun": {"deps": ["six"]}}


@pytest.mark.skipif(not fs_supports_symlink(), reason="creating symlinks needs privileges")
@pytest.mark.parametrize(
    "target_content",
    [
        pytest.param("must survive", id="non-json"),
        pytest.param('{"ToxEnv": {"name": "a"}}', id="matching-state"),
        pytest.param('{"private": "must survive"}', id="other-data"),
    ],
)
def test_info_write_replaces_symlink(tmp_path: Path, target_content: str) -> None:
    victim: Final[Path] = tmp_path / "outside" / "notes.txt"
    victim.parent.mkdir()
    victim.write_text(target_content)
    env_dir: Final[Path] = tmp_path / "env"
    env_dir.mkdir()
    state: Final[Path] = env_dir / ".tox-info.json"
    state.symlink_to(victim)

    with Info(env_dir).compare({"name": "a"}, "ToxEnv") as (eq, old):
        assert (eq, old) == (False, None)

    assert victim.read_text() == target_content
    assert not state.is_symlink()
    assert json.loads(state.read_text()) == {"ToxEnv": {"name": "a"}}
    assert [p.name for p in env_dir.iterdir()] == [".tox-info.json"]


def test_info_write_failure_cleans_temp_file(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("tox.tox_env.info.Path.replace", autospec=True, side_effect=OSError("boom"))

    with pytest.raises(OSError, match="boom"), Info(tmp_path).compare({"name": "a"}, "ToxEnv"):
        pass

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("content", "section", "sub_section", "expected"),
    [
        pytest.param(
            '{"Python": []}',
            "Python",
            None,
            {"Python": {"base_python": ["3.14"]}},
            id="whole section",
        ),
        pytest.param(
            '{"PythonRun": {"deps": []}}',
            "PythonRun",
            "deps",
            {"PythonRun": {"deps": {"base_python": ["3.14"]}}},
            id="nested section",
        ),
    ],
)
def test_info_non_dict_mapping_section_self_heals(
    tmp_path: Path,
    content: str,
    section: str,
    sub_section: str | None,
    expected: dict[str, dict[str, list[str] | dict[str, list[str]]]],
) -> None:
    (tmp_path / ".tox-info.json").write_text(content)

    with Info(tmp_path).compare({"base_python": ["3.14"]}, section, sub_section) as (eq, old):
        assert (eq, old) == (False, None)

    assert json.loads((tmp_path / ".tox-info.json").read_text()) == expected
