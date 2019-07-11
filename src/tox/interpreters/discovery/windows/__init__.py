from __future__ import unicode_literals

from ..py_info import PythonInfo
from ..py_spec import PythonSpec
from .pep514 import discover_pythons


def propose_interpreters(spec):
    # see if PEP-514 entries are good
    for name, major, minor, arch, exe, _ in discover_pythons():
        # pre-filter
        our = PythonSpec(None, name, major, minor, None, arch, exe)
        if our.satisfies(spec):
            interpreter = PythonInfo.from_exe(exe, raise_on_error=False)
            if interpreter is not None:
                yield interpreter
