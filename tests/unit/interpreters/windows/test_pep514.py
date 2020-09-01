from __future__ import unicode_literals

import inspect
import subprocess
import sys

from tox._pytestplugin import mark_dont_run_on_posix


@mark_dont_run_on_posix
def test_discover_winreg():
    from tox.interpreters.windows.pep514 import discover_pythons

    list(discover_pythons())  # raises no error


@mark_dont_run_on_posix
def test_run_pep514_main_no_warnings():
    # check we trigger no warnings
    import tox.interpreters.windows.pep514 as pep514

    out = subprocess.check_output(
        [sys.executable, inspect.getsourcefile(pep514)],
        universal_newlines=True,
    )
    assert "PEP-514 violation in Windows Registry " not in out, out
