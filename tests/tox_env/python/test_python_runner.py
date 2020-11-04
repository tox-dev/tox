from tox.pytest import ToxProjectCreator


def test_deps_config_path_req(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv:py]\ndeps =-rpath.txt\n -r{toxinidir}/path.txt\n pytest"})
    result = project.run("c", "-e", "py")
    result.assert_success()
    deps = result.state.conf.get_env("py")["deps"]
    assert len(deps) == 3
    assert deps[0].value == project.path / "path.txt"
    assert deps[1].value == project.path / "path.txt"
    assert str(deps[2].value) == "pytest"
