from tox.pytest import ToxProjectCreator


def test_quickstart(tox_project: ToxProjectCreator) -> None:
    project = tox_project({})
    outcome = project.run("q")
    outcome.assert_success()
    out = (
        f"ROOT: No tox.ini or pyproject.toml found, assuming empty tox.ini at {project.path / 'tox.ini'}\n"
        "done quickstart\n"
    )
    outcome.assert_out_err(out, "")
