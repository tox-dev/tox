from __future__ import annotations

from pathlib import Path

from tox.tox_env.info import Info


def test_info_repr() -> None:
    at_loc = Path().absolute()
    info_object = Info(at_loc)
    assert repr(info_object) == f"Info(path={at_loc / '.tox-info.json'})"
