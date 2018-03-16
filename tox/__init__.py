import os
import signal

from pkg_resources import DistributionNotFound
from pkg_resources import get_distribution

from .hookspecs import hookimpl
from .hookspecs import hookspec

try:
    _full_version = get_distribution(__name__).version
    __version__ = _full_version.split('+', 1)[0]
except DistributionNotFound:
    __version__ = '0.0.0.dev0'


# separate function because pytest-mock `spy` does not work on Exceptions
# can use neither a class method nor a static because of
# https://bugs.python.org/issue23078
# even a normal method failed with
# TypeError: descriptor '__getattribute__' requires a 'BaseException' object but received a 'type'
def _exit_code_str(exception_name, command, exit_code):
    """ string representation for an InvocationError, with exit code """
    str_ = "%s for command %s" % (exception_name, command)
    if exit_code is not None:
        str_ += " (exited with code %d)" % (exit_code)
        if (os.name == 'posix') and (exit_code > 128):
            signals = {number: name
                       for name, number in vars(signal).items()
                       if name.startswith("SIG")}
            number = exit_code - 128
            name = signals.get(number)
            if name:
                str_ += ("\nNote: this might indicate a fatal error signal "
                         "({} - 128 = {}: {})".format(number+128, number, name))
    return str_


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
        def __init__(self, command, exit_code=None):
            super(exception.Error, self).__init__(command, exit_code)
            self.command = command
            self.exit_code = exit_code

        def __str__(self):
            return _exit_code_str(self.__class__.__name__, self.command, self.exit_code)

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


from .session import run_main as cmdline  # noqa

__all__ = ('hookspec', 'hookimpl', 'cmdline', 'exception', '__version__')
