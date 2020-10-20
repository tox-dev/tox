"""Common functionality shared across multiple type of runs"""
from argparse import ArgumentParser


def env_run_create_flags(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-r",
        "--recreate",
        dest="recreate",
        help="recreate the tox environments",
        action="store_true",
    )
    parser.add_argument("-n", "--notest", dest="no_test", help="do not run the test commands", action="store_true")
