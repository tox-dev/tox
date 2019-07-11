from __future__ import unicode_literals

import os
import sys
from distutils.spawn import find_executable

from .py_info import CURRENT, PythonInfo
from .py_spec import PythonSpec

IS_WIN = sys.platform == "win32"


def get_interpreter(key):
    spec = PythonSpec.from_string_spec(key)
    for interpreter, impl_must_match in propose_interpreters(spec):
        if interpreter.satisfies(spec, impl_must_match):
            return interpreter
    return None


def propose_interpreters(spec):
    # 1. we always try with the lowest hanging fruit first, the current interpreter
    yield CURRENT, True

    # 2. then maybe it's something exact on PATH - if it was direct lookup implementation no longer counts
    interpreter = find_on_path(spec.str_spec)
    if interpreter is not None:
        yield interpreter, False

    # 3. otherwise fallback to platform logic
    if IS_WIN:
        from .windows import propose_interpreters

        for interpreter in propose_interpreters(spec):
            yield interpreter, True

    # 4. or from the spec we can deduce a name on path  that matches
    for exe in spec.generate_paths():
        interpreter = find_on_path(exe)
        if interpreter is not None:
            yield interpreter, True


def find_on_path(key):
    exe = find_executable(key)
    if exe is not None:
        exe = os.path.abspath(exe)
        interpreter = PythonInfo.from_exe(exe, raise_on_error=False)
        return interpreter
