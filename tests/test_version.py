def test_version() -> None:
    from tox.version import __version__

    assert __version__
