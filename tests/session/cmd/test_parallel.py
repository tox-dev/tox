from tox.pytest import ToxProjectCreator


def test_parallel_run(tox_project: ToxProjectCreator) -> None:
    ini = """
    [tox]
    no_package=true
    env_list= a, b, c
    [testenv]
    commands=python -c 'print("{env_name}")'
    depends = !c: c
    """
    project = tox_project({"tox.ini": ini})
    outcome = project.run("p")
    outcome.assert_success()

    out = outcome.out
    for env in "a", "b", "c":
        env_done = f"{env}: OK ✔"
        env_report = f"  {env}: OK ("

        assert env_done in out, out
        assert env_report in out, out
        assert out.index(env_done) < out.index(env_report), out
