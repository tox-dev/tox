from __future__ import annotations


def test_version() -> None:
    from tox import __version__

    assert __version__
