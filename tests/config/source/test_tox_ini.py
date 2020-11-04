from tests.conftest import ToxIniCreator


def test_tox_ini_core(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf("[tox]")
    core_loader_1 = list(config._src.get_core({}))
    assert len(core_loader_1) == 1

    core_loader_2 = list(config._src.get_core({}))
    assert len(core_loader_2) == 1

    assert core_loader_1[0] is core_loader_2[0]
