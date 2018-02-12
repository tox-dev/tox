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
            str_ = "%s for command %s" % (self.__class__.__name__, self.command)
            if self.exit_code is not None:
                str_ += " (exited with code %d)" % (self.exit_code)
                if self.exit_code > 128:
                    signals = {number: name
                               for name, number in vars(signal).items()
                               if name.startswith("SIG")}
                    number = self.exit_code - 128
                    name = signals.get(number)
                    (eg_number, eg_name) = (number, name) if name else (11, "SIGSEGV")
                    str_ += ("\nNote: On unix systems, an exit code larger than 128 often "
                             "means a fatal error signal "
                             "(e.g. {}=128+{}: {})".format(eg_number+128, eg_number, eg_name))
            return str_

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


from .session import main as cmdline  # noqa

__all__ = ('hookspec', 'hookimpl', 'cmdline', 'exception', '__version__')
