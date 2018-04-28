import pluggy
from pkg_resources import DistributionNotFound
from pkg_resources import get_distribution

from . import exception
from .constants import INFO
from .constants import PIP
from .constants import PYTHON
from .hookspecs import hookspec

__all__ = (
    'cmdline', 'exception', '__version__',
    'PYTHON', 'INFO', 'PIP',
    'hookimpl',
    'hookspec',  # DEPRECATED will be removed from API - see warning below
)
"""Everything explicitly exported here is part of the tox programmatic API.

To override/modify tox behaviour via plugins see tox.hookspec and its use with pluggy.
"""

hookimpl = pluggy.HookimplMarker("tox")
"""Hook implementation marker to be imported by plugins."""

try:
    _full_version = get_distribution(__name__).version
    __version__ = _full_version.split('+', 1)[0]
except DistributionNotFound:
    __version__ = '0.0.0.dev0'


# NOTE: must come last due to circular import
from .session import cmdline  # noqa
