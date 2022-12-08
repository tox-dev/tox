from __future__ import annotations

from io import BytesIO

import pytest
from colorama import Fore

from tox.execute.stream import SyncWrite


def test_sync_write_repr() -> None:
    sync_write = SyncWrite(name="a", target=None, color=Fore.RED)
    assert repr(sync_write) == f"SyncWrite(name='a', target=None, color={Fore.RED!r})"


@pytest.mark.parametrize("encoding", ("utf-8", "latin-1", "cp1252"))
def test_sync_write_encoding(encoding) -> None:
    text = "Hello W\N{LATIN SMALL LETTER O WITH DIAERESIS}rld: "
    io = BytesIO()

    sync_write = SyncWrite(name="a", target=io, color=Fore.RED, encoding=encoding)
    sync_write.handler(text.encode(encoding))
    assert sync_write.text == text


@pytest.mark.parametrize("encoding", ("latin-1", "cp1252"))
def test_sync_invalid_encoding(encoding) -> None:
    text = "Hello W\N{LATIN SMALL LETTER O WITH DIAERESIS}rld: "
    io = BytesIO()

    sync_write = SyncWrite(name="a", target=io, color=Fore.RED, encoding="utf-8")
    sync_write.handler(text.encode(encoding))
    with pytest.raises(UnicodeDecodeError):
        assert sync_write.text == text
