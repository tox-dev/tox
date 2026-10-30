from __future__ import annotations

import json
from pathlib import Path

import pytest

from tox.tox_env.info import Info


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
