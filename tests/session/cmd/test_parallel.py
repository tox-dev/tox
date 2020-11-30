from tox.pytest import ToxProjectCreator


def test_parallel_run(tox_project: ToxProjectCreator) -> None:
    ini = """
    [tox]
    no_package=true
    env_list= a, b, c
    [testenv]
    commands=python -c 'print("run {env_name}")'
    depends = !c: c
    parallel_show_output = c: true
    """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("p")
    outcome.assert_success()

    out = outcome.out
    for env in "a", "b", "c":
        if env == "c":
            assert "run c" in out, out
        else:
            assert f"run {env}" not in out, out

        env_done = f"{env}: OK ✔"
        assert env_done in out, out

        env_report = f"  {env}: OK ("
        assert env_report in out, out
        assert out.index(env_done) < out.index(env_report), out
