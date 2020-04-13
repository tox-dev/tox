from asyncio.windows_utils import BUFSIZE, PipeHandle

import _overlapped

from .read_via_thread import ReadViaThread


class ReadViaThreadWindows(ReadViaThread):
    def __init__(self, stream, handler):
        super().__init__(stream, handler)
        assert isinstance(stream, PipeHandle)
        self._io_cp = _overlapped.CreateIoCompletionPort(self.stream.handle, 0, 0, 1)
        self._ov = _overlapped.Overlapped(0)

    @property
    def closed(self):
        """check if the stream is closed or not"""
        return self.stream.handle is None

    def has_bytes(self):
        """check weather the stream has any bytes ready to read"""
        result = _overlapped.GetQueuedCompletionStatus(self._io_cp, 10)  # 10 ms to wait
        return result

    def _read_bytes(self):
        """read all available (non-blocking) bytes from an overlapped opened file handler"""
        try:
            res = bytearray(BUFSIZE)
            self._ov.ReadFileInto(self.stream.handle, res)
            try:
                length = res.index(b"\x00")
            except ValueError:
                length = len(res)
            data = res[:length]
            return data
        except BrokenPipeError:
            return None
