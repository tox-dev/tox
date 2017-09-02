from collections import defaultdict

from pkg_resources import get_distribution, DistributionNotFound

from .hookspecs import hookspec, hookimpl  # noqa

try:
    _full_version = get_distribution(__name__).version
    __version__ = _full_version.split('+', 1)[0]
except DistributionNotFound:
    __version__ = '0.0.0.dev0'


class exception:
    class Error(Exception):
        def __str__(self):
            return "%s: %s" % (self.__class__.__name__, self.args[0])

    class ConfigError(Error):
        """ error in tox configuration. """
    class UnsupportedInterpreter(Error):
        "signals an unsupported Interpreter"
    class InterpreterNotFound(Error):
        "signals that an interpreter could not be found"
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


missing_env_substitution_map = defaultdict(list)  # FIXME - UGLY HACK
"""Map section name to env variables that would be needed in that section but are not provided.

Pre 2.8.1 missing substitutions crashed with a ConfigError although this would not be a problem
if the env is not part of the current testrun. So we need to remember this and check later
when the testenv is actually run and crash only then.
"""

from tox.session import main as cmdline  # noqa
