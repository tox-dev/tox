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
    'hookspec', 'hookimpl',  # DEPRECATED will be removed from API - see warning below
)
"""Everything explicitly exported here is part of the tox programmatic API.

To override/modify tox behaviour via plugins see tox.hookspec and its use with pluggy.
"""

hookimpl = pluggy.HookimplMarker("tox")
"""DEPRECATED - REMOVE - this should never be imported from anywhere
# Instead instantiate the hookimpl by using exactly this call in your plugin code
"""

try:
    _full_version = get_distribution(__name__).version
    __version__ = _full_version.split('+', 1)[0]
except DistributionNotFound:
    __version__ = '0.0.0.dev0'


# NOTE: must come last due to circular import
from .session import cmdline  # noqa
