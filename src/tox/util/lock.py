"""holds locking functionality that works across processes"""
from __future__ import absolute_import, unicode_literals

from contextlib import contextmanager

import py
from filelock import FileLock, Timeout


@contextmanager
def get(lock_file, report):
    py.path.local(lock_file.dirname).ensure(dir=1)
    lock = FileLock(str(lock_file))
    try:
        try:
            lock.acquire(0.0001)
        except Timeout:
            report("lock file {} present, will block until released".format(lock_file))
            lock.acquire()
        yield
    finally:
        lock.release(force=True)


def get_unique_file(path, prefix, suffix, report):
    """get a unique file in a folder having a given prefix and suffix,
    with unique number in between"""
    lock_file = path.join(".lock")
    prefix = "{}-".format(prefix)
    with get(lock_file, report):
        max_value = -1
        for candidate in path.listdir("{}*{}".format(prefix, suffix)):
            try:
                max_value = max(max_value, int(candidate.name[len(prefix) : -len(suffix)]))
            except ValueError:
                continue
        winner = path.join("{}{}.log".format(prefix, max_value + 1))
        winner.ensure(dir=0)
        return winner
