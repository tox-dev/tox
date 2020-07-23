from tox._pytestplugin import mark_dont_run_on_posix


@mark_dont_run_on_posix
def test_locate_via_pep514(monkeypatch):
    import tox.interpreters.windows
    from tox.interpreters.py_spec import CURRENT

    del tox.interpreters.windows._PY_AVAILABLE[:]
    exe = tox.interpreters.windows.locate_via_pep514(CURRENT)
    assert exe
    assert len(tox.interpreters.windows._PY_AVAILABLE)

    import tox.interpreters.windows.pep514

    def raise_on_call():
        raise RuntimeError()

    monkeypatch.setattr(tox.interpreters.windows.pep514, "discover_pythons", raise_on_call)
    assert tox.interpreters.windows.locate_via_pep514(CURRENT)
