from __future__ import absolute_import, unicode_literals

from argparse import ArgumentTypeError

ENV_VAR_KEY = "_PARALLEL_TOXENV"
OFF_VALUE = 0
DEFAULT_PARALLEL = OFF_VALUE


def auto_detect_cpus():
    try:
        from os import sched_getaffinity
    except ImportError:
        try:
            from os import cpu_count
        except ImportError:
            from multiprocessing import cpu_count
    else:

        def cpu_count():
            return len(sched_getaffinity(0))

    try:
        n = cpu_count()
    except NotImplementedError:
        return 1
    return n if n else 1


def parse_num_processes(s):
    if s == "all":
        return None
    if s == "auto":
        return auto_detect_cpus()
    else:
        value = int(s)
        if value < 0:
            raise ArgumentTypeError("value must be positive")
        return value


def add_parallel_flags(parser):
    parser.add_argument(
        "-p",
        "--parallel",
        dest="parallel",
        help="run tox environments in parallel, the argument controls limit: all,"
        " auto - cpu count, some positive number, zero is turn off",
        action="store",
        type=parse_num_processes,
        default=DEFAULT_PARALLEL,
    )
    parser.add_argument(
        "-o",
        "--parallel-live",
        action="store_true",
        dest="parallel_live",
        help="connect to stdout while running environments",
    )
