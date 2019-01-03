from __future__ import absolute_import, unicode_literals

from argparse import ArgumentTypeError

ENV_VAR_KEY = "TOX_PARALLEL_ENV"
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


def add_parallel_config(parser):
    def depends_check(testenv_config, value):
        if value:
            pass
        return value

    parser.add_testenv_attribute(
        "depends",
        type="env-list",
        help="tox environments that this environment depends on (must be run after those)",
        postprocess=depends_check,
    )

    parser.add_testenv_attribute(
        "parallel_show_output",
        type="bool",
        default=False,
        help="if set to True the content of the output will always be shown "
        "when running in parallel mode",
    )
