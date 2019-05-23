from __future__ import unicode_literals

from tox._pytestplugin import mark_dont_run_on_posix


@mark_dont_run_on_posix
def test_discover_winreg():
    from tox.interpreters.windows.pep514 import discover_pythons

    list(discover_pythons())
