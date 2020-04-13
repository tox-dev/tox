import os
import select

from .read_via_thread import ReadViaThread


class ReadViaThreadUnix(ReadViaThread):
    def __init__(self, stream, handler):
        super().__init__(stream, handler)
        self.file_no = self.stream.fileno()

    @property
    def closed(self):
        return self.stream.closed

    def has_bytes(self):
        read_available_list, _, __ = select.select([self.stream], [], [], 0.01)
        return len(read_available_list)

    def _read_bytes(self):
        return os.read(self.file_no, 1)
