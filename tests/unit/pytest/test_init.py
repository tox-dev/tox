from tox.pytest import check_os_environ


def test_init_base(tox_project):
    project = tox_project(
        {
            "tox.ini": """
            [tox]
            """,
            "src": {"__init__.py": "pass", "a": "out", "b": {"c": "out"}, "e": {"f": ""}},
        }
    )
    assert str(project.path) in repr(project)
    assert project.path.exists()
    assert project.structure == {
        "tox.ini": "\n[tox]\n",
        "src": {"__init__.py": "pass", "a": "out", "e": {"f": ""}, "b": {"c": "out"}},
    }


def test_env_var(monkeypatch):
    monkeypatch.setenv("MORE", "B")
    monkeypatch.setenv("EXTRA", "1")
    monkeypatch.setenv("PYTHONPATH", "yes")
    gen = check_os_environ()
    next(gen)
    monkeypatch.setenv("MAGIC", "A")
    monkeypatch.setenv("MORE", "D")
    monkeypatch.delenv("EXTRA")

    from tox.pytest import pytest as tox_pytest

    exp = "test changed environ extra {'MAGIC': 'A'} miss {'EXTRA': '1'} diff {'MORE = B vs D'}"

    def fail(msg):
        assert msg == exp

    monkeypatch.setattr(tox_pytest, "fail", fail)
    try:
        gen.send(None)
    except StopIteration:
        pass
