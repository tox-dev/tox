from abc import ABC, abstractmethod
from threading import Event, Thread

WAIT_GENERAL = 0.1


class ReadViaThread(ABC):
    def __init__(self, stream, handler):
        self.stream = stream
        self.stop = Event()
        self.thread = Thread(target=self._read_stream)
        self.handler = handler

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        thrown = None
        while True:
            try:
                self.stop.set()
                while self.thread.is_alive():
                    self.thread.join(WAIT_GENERAL)
            except KeyboardInterrupt as exception:  # pragma: no cover
                thrown = exception  # pragma: no cover
                continue  # pragma: no cover
            else:
                if thrown is not None:
                    raise thrown  # pragma: no cover
                else:  # pragma: no cover
                    break  # pragma: no cover
        if exc_val is None:  # drain what remains if we were not interrupted
            try:
                data = self._read_bytes()
            except ValueError:  # pragma: no cover
                pass  # pragma: no cover
            else:
                while True:
                    try:
                        self.handler(data)
                        break
                    except KeyboardInterrupt as exception:  # pragma: no cover
                        thrown = exception  # pragma: no cover
                if thrown is not None:
                    raise thrown  # pragma: no cover

    def _read_stream(self):
        while not (self.closed or self.stop.is_set()):
            # we need to drain the stream, but periodically give chance for the thread to break if the stop event has
            # been set (this is so that an interrupt can be handled)
            if self.has_bytes():
                data = self._read_bytes()
                self.handler(data)

    @property
    @abstractmethod
    def closed(self):
        raise NotImplementedError

    @abstractmethod
    def has_bytes(self):
        raise NotImplementedError

    @abstractmethod
    def _read_bytes(self) -> bytes:
        raise NotImplementedError
