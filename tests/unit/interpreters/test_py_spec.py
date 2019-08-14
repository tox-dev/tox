from tox.interpreters.py_spec import PythonSpec


def test_py_3_10():
    spec = PythonSpec.from_name("python3.10")
    assert (spec.major, spec.minor) == (3, 10)
