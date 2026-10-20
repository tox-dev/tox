"""Helper methods related to the CPU."""

from __future__ import annotations

import os
import sys


def auto_detect_cpus() -> int:
    """:returns: the number of CPUs this process may run on, honouring the CPU affinity mask (``taskset``, cpusets)"""
    if sys.version_info >= (3, 13):  # pragma: >=3.13 cover
        n = os.process_cpu_count()  # also honours PYTHON_CPU_COUNT and -X cpu_count
    elif hasattr(os, "sched_getaffinity"):  # pragma: <3.13 cover
        n = len(os.sched_getaffinity(0))
    else:  # pragma: <3.13 cover # macOS and Windows expose no affinity mask before 3.13
        n = os.cpu_count()
    return n or 1


__all__ = ("auto_detect_cpus",)
