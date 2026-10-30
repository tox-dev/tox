from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

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


def test_info_write_replaces_symlink_instead_of_following(tmp_path: Path) -> None:
    victim = tmp_path / "outside" / "notes.txt"
    victim.parent.mkdir()
    victim.write_text("must survive")
    env_dir = tmp_path / "env"
    env_dir.mkdir()
    state = env_dir / ".tox-info.json"
    try:
        state.symlink_to(victim)
    except OSError:  # pragma: no cover # Windows without symlink privilege
        pytest.skip("symlinks not supported")

    with Info(env_dir).compare({"name": "a"}, "ToxEnv") as (eq, _):
        assert not eq

    assert victim.read_text() == "must survive"
    assert not state.is_symlink()
    assert json.loads(state.read_text()) == {"ToxEnv": {"name": "a"}}
    assert [p.name for p in env_dir.iterdir()] == [".tox-info.json"]


def test_info_write_failure_cleans_temp_file(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("tox.tox_env.info.Path.replace", side_effect=OSError("boom"))

    with pytest.raises(OSError, match="boom"), Info(tmp_path).compare({"name": "a"}, "ToxEnv"):
        pass

    assert list(tmp_path.iterdir()) == []
