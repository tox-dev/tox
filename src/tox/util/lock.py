"""holds locking functionality that works across processes"""

import logging
from contextlib import contextmanager

import py
from filelock import FileLock, Timeout


@contextmanager
def hold_lock(lock_file):
    py.path.local(lock_file.dirname).ensure(dir=1)
    lock = FileLock(str(lock_file))
    try:
        try:
            lock.acquire(0.0001)
        except Timeout:
            logging.warning(f"lock file {lock_file} present, will block until released")
            lock.acquire()
        yield
    finally:
        lock.release(force=True)


def get_unique_file(path, prefix, suffix):
    """get a unique file in a folder having a given prefix and suffix, with unique number in between"""
    lock_file = path.join(".lock")
    prefix = f"{prefix}-"
    with hold_lock(lock_file):
        max_value = -1
        for candidate in path.listdir(f"{prefix}*{suffix}"):
            try:
                max_value = max(max_value, int(candidate.basename[len(prefix) : -len(suffix)]))
            except ValueError:
                continue
        winner = path.join(f"{prefix}{max_value + 1}{suffix}")
        winner.ensure(dir=0)
        return winner
