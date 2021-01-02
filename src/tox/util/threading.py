from threading import Lock


class AtomicCounter:
    def __init__(self) -> None:
        self.value: int = 0
        self._lock = Lock()

    def increment(self) -> None:
        with self._lock:
            self.value += 1

    def decrement(self) -> None:
        with self._lock:
            self.value -= 1
