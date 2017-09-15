from pkg_resources import DistributionNotFound
from pkg_resources import get_distribution

from .hookspecs import hookimpl
from .hookspecs import hookspec

try:
    _full_version = get_distribution(__name__).version
    __version__ = _full_version.split('+', 1)[0]
except DistributionNotFound:
    __version__ = '0.0.0.dev0'


class exception:
    class Error(Exception):
        def __str__(self):
            return "%s: %s" % (self.__class__.__name__, self.args[0])

    class MissingSubstitution(Error):
        FLAG = 'TOX_MISSING_SUBSTITUTION'
        """placeholder for debugging configurations"""
        def __init__(self, name):
            self.name = name

    class ConfigError(Error):
        """ error in tox configuration. """
    class UnsupportedInterpreter(Error):
        """signals an unsupported Interpreter"""
    class InterpreterNotFound(Error):
        """signals that an interpreter could not be found"""
    class InvocationError(Error):
        """ an error while invoking a script. """
    class MissingFile(Error):
        """ an error while invoking a script. """
    class MissingDirectory(Error):
        """ a directory did not exist. """
    class MissingDependency(Error):
        """ a dependency could not be found or determined. """
    class MinVersionError(Error):
        """ the installed tox version is lower than requested minversion. """

        def __init__(self, message):
            self.message = message
            super(exception.MinVersionError, self).__init__(message)


from tox.session import main as cmdline  # noqa

__all__ = ('hookspec', 'hookimpl', 'cmdline', 'exception', '__version__')
