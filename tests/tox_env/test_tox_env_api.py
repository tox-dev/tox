from tox.pytest import MonkeyPatch, ToxProjectCreator


def test_requirements_txt(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\nrecreate=True"})
    result_first = prj.run("r")
    result_first.assert_success()

    result_second = prj.run("r")
    result_second.assert_success()
    assert "remove tox env folder" in result_second.out
