from __future__ import annotations

from colorama import Fore

from tox.execute.stream import SyncWrite


def test_sync_write_repr() -> None:
    sync_write = SyncWrite(name="a", target=None, color=Fore.RED)
    assert repr(sync_write) == f"SyncWrite(name='a', target=None, color={Fore.RED!r})"


def test_sync_write_decode_surrogate() -> None:
    sync_write = SyncWrite(name="a", target=None)
    sync_write.handler(b"\xed\n")
    assert sync_write.text == "\udced\n"
