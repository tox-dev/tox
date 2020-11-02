from tox.pytest import ToxProjectCreator


def test_tox_ini_core(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[tox]"})
    config = project.config()
    core_loader_1 = list(config._src.get_core({}))
    assert len(core_loader_1) == 1

    core_loader_2 = list(config._src.get_core({}))
    assert len(core_loader_2) == 1

    assert core_loader_1[0] is core_loader_2[0]
