import logging
import sys
import threading
from signal import Handlers, Signals, signal
from types import FrameType, TracebackType
from typing import Callable, Optional, Type, Union

if sys.platform == "win32":  # pragma: win32 cover
    from signal import CTRL_C_EVENT as SIGINT
else:
    from signal import SIGINT


class DelayedSignal:
    def __init__(self, of: Signals = SIGINT) -> None:
        self._of = of
        self._signal: Optional[Signals] = None
        self._frame: Optional[FrameType] = None
        self._old_handler: Union[Callable[[Signals, FrameType], None], int, Handlers, None] = None

    def __enter__(self) -> None:
        self._signal, self._frame = None, None
        if threading.current_thread() == threading.main_thread():  # signals are always handled on the main thread only
            self._old_handler = signal(self._of, self._handler)

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        try:
            if self._signal is not None and self._frame is not None and callable(self._old_handler):
                logging.debug("Handling delayed %s", self._signal)
                self._old_handler(self._signal, self._frame)
        finally:
            if self._old_handler is not None:
                signal(self._of, self._old_handler)

    def _handler(self, sig: Signals, frame: FrameType) -> None:
        logging.debug("Received %s, delaying it", sig)
        self._signal, self._frame = sig, frame


__all__ = (
    "DelayedSignal",
    "SIGINT",
)
