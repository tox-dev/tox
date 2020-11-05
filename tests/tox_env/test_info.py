from pathlib import Path

from tox.tox_env.info import Info


def test_Info_dunder_repr_method() -> None:
    info_object = Info(Path())
    assert repr(info_object) == "Info(path=.tox-info.json)"
