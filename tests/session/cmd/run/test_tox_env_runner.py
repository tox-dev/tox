from tox.pytest import ToxProjectCreator


def test_ignore_cmd(tox_project: ToxProjectCreator) -> None:
    cmd = [
        "- python -c 'import sys; print(\"magic fail\", file=sys.stderr); sys.exit(1)'",
        "python -c 'import sys; print(\"magic pass\"); sys.exit(0)'",
    ]
    project = tox_project({"tox.ini": f"[tox]\nenvlist=py\nno_package=true\n[testenv]\ncommands={cmd[0]}\n {cmd[1]}"})
    outcome = project.run("r", "-e", "py")
    outcome.assert_success()
    assert "magic pass" in outcome.out
    assert "magic fail" in outcome.err
