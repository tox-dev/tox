from __future__ import unicode_literals
import sys

from tox import reporter
import tox

from .common import base_discover
from .via_path import check_with_path


@tox.hookimpl
def tox_get_python_executable(envconfig):
    """
    Return path to specified interpreter.
    If not available, exit(1).
    """
    spec, path = base_discover(envconfig)

    if path is None:
        reporter.error('envname {} not found'.format(envconfig.envname))
        sys.exit(1)
    else:
        return path
~
