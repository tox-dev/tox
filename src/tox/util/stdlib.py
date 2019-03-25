import sys
import threading


def is_main_thread():
    cur_thread = threading.current_thread()
    if sys.version_info >= (3, 4):
        return cur_thread is threading.main_thread()
    else:
        # noinspection PyUnresolvedReferences
        return isinstance(cur_thread, threading._MainThread)
