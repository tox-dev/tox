import pluggy
from pkg_resources import DistributionNotFound
from pkg_resources import get_distribution

from .exc import exception  # noqa
from .hookspecs import hookspec

# NOTE: hookimpl and hookspec objects will be removed from API in tox 4 - see warning below
__all__ = ('hookspec', 'hookimpl', 'cmdline', 'exception', '__version__')
"""Everything explicitly exported here is part of the tox programmatic API.

To override/modify tox behaviour also see tox.hookspec and its use with pluggy.

"""

# DEPRECATED - will go away in tox 4
# this should never be imported from anywhere
# Instead instantiate the hookimpl by using exactly this call in your plugin code
hookimpl = pluggy.HookimplMarker("tox")

try:
    _full_version = get_distribution(__name__).version
    __version__ = _full_version.split('+', 1)[0]
except DistributionNotFound:
    __version__ = '0.0.0.dev0'


# NOTE: must come last due to circular import
from .session import cmdline  # noqa
