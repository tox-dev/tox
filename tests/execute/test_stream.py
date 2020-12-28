from colorama import Fore

from tox.execute.stream import SyncWrite


def test_sync_write_repr() -> None:
    sync_write = SyncWrite(name="a", target=None, color=Fore.RED)
    assert repr(sync_write) == f"SyncWrite(name='a', target=None, color={Fore.RED!r})"
