import pytest

from tox.interpreters.discovery.py_spec import PythonSpec


@pytest.mark.parametrize(
    "spec, outcome",
    [
        ("python3.7", PythonSpec("python3.7", "CPython", 3, 7, None, None, None)),
        ("python3.7.1", PythonSpec("python3.7.1", "CPython", 3, 7, 1, None, None)),
        ("python3.7.1-32", PythonSpec("python3.7.1-32", "CPython", 3, 7, 1, 32, None)),
        ("python3.7.1-64", PythonSpec("python3.7.1-64", "CPython", 3, 7, 1, 64, None)),
        (
            "python3.7.1-65",
            PythonSpec("python3.7.1-65", None, None, None, None, None, "python3.7.1-65"),
        ),
        ("python3.6", PythonSpec("python3.6", "CPython", 3, 6, None, None, None)),
        ("python37", PythonSpec("python37", "CPython", 3, 7, None, None, None)),
        ("python36", PythonSpec("python36", "CPython", 3, 6, None, None, None)),
        ("py37", PythonSpec("py37", "CPython", 3, 7, None, None, None)),
        ("py36", PythonSpec("py36", "CPython", 3, 6, None, None, None)),
        ("py3.7.8.1", PythonSpec("py3.7.8.1", None, None, None, None, None, "py3.7.8.1")),
    ],
)
def test_spec(spec, outcome):
    assert PythonSpec.from_string_spec(spec) == outcome
