from tox.interpreters.py_spec import PythonSpec


def test_py_3_10():
    spec = PythonSpec.from_name("python3.10")
    assert (spec.major, spec.minor) == (3, 10)


def test_debug_python():
    spec = PythonSpec.from_name("python3.10-dbg")
    assert (spec.major, spec.minor) == (None, None)


def test_parse_architecture():
    spec = PythonSpec.from_name("python3.10-32")
    assert (spec.major, spec.minor, spec.architecture) == (3, 10, 32)
