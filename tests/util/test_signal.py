import logging
import os
import sys
from threading import Thread
from time import sleep

import pytest

from tox.execute.local_sub_process import SIG_INTERRUPT
from tox.pytest import LogCaptureFixture
from tox.util.signal import DelayedSignal


@pytest.mark.skipif(sys.platform == "win32", reason="You need a conhost shell for keyboard interrupt")
def test_signal_delayed(caplog: LogCaptureFixture) -> None:
    caplog.set_level(level=logging.DEBUG)
    with pytest.raises(KeyboardInterrupt):
        with DelayedSignal() as handler:
            try:
                os.kill(os.getpid(), SIG_INTERRUPT)
                while True:
                    sleep(0.05)
                    if handler._signal is not None:  # pragma: no branch
                        break
            except KeyboardInterrupt:  # pragma: no cover
                assert False  # pragma: no cover
    assert caplog.messages == [
        "Received 2, delaying it",
        "Handling delayed 2",
    ]


def test_signal_no_op_background(caplog: LogCaptureFixture) -> None:
    caplog.set_level(level=logging.DEBUG)

    def _run() -> None:
        with DelayedSignal():
            pass

    thread = Thread(target=_run)
    thread.start()
    thread.join()
    assert caplog.messages == []
