"""Helper methods related to the CPU"""
import multiprocessing
from typing import Optional


def auto_detect_cpus() -> int:
    try:
        n: Optional[int] = multiprocessing.cpu_count()
    except NotImplementedError:
        n = None
    return n if n else 1


__all__ = ("auto_detect_cpus",)
