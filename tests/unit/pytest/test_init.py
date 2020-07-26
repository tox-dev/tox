from tox.pytest import check_os_environ


def test_init_base(tox_project):
    project = tox_project(
        {
            "tox.ini": """
            [tox]
            """,
            "src": {"__init__.py": "pass", "a": "out", "b": {"c": "out"}, "e": {"f": ""}},
        },
    )
    assert str(project.path) in repr(project)
    assert project.path.exists()
    assert project.structure == {
        "tox.ini": "\n[tox]\n",
        "src": {"__init__.py": "pass", "a": "out", "e": {"f": ""}, "b": {"c": "out"}},
    }


def test_env_var(monkeypatch):
    with monkeypatch.context() as m:
        m.setenv("MORE", "B")
        m.setenv("EXTRA", "1")
        m.setenv("PYTHONPATH", "yes")

        with check_os_environ():
            m.setenv("MAGIC", "A")
            m.setenv("MORE", "D")
            m.delenv("EXTRA")

            from tox.pytest import pytest as tox_pytest

            exp = "test changed environ extra {'MAGIC': 'A'} miss {'EXTRA': '1'} diff {'MORE = B vs D'}"

            def fail(msg):
                assert msg == exp

            m.setattr(tox_pytest, "fail", fail)
