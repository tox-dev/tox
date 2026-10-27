"""Helper methods related to the CPU."""

from __future__ import annotations

import os
import sys


def auto_detect_cpus() -> int:
    if sys.version_info >= (3, 13):  # pragma: >=3.13 cover
        count = os.process_cpu_count()
    elif hasattr(os, "sched_getaffinity"):  # pragma: <3.13 cover
        count = len(os.sched_getaffinity(0))
    else:  # pragma: <3.13 cover # macOS and Windows expose no CPU affinity
        count = os.cpu_count()
    return count or 1


__all__ = ("auto_detect_cpus",)
