from __future__ import absolute_import, unicode_literals

from tox import cmdline
from tox.config import parallel


def run():
    parallel.DEFAULT_PARALLEL = "auto"
    cmdline()


__all__ = ("run",)
