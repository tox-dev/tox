#
__version__ = "0.5a2"

import apipkg

apipkg.initpkg(__name__, dict(
    cmdline   = '._cmdline:main',
    exception = dict(
        ConfigError = '._config:ConfigError',
        InvocationError = '._exception:InvocationError',
        MissingDependency= '._exception:MissingDependency',
        UnsupportedInterpreter = '._exception:UnsupportedInterpreter',
        InterpreterNotFound = '._exception:InterpreterNotFound',
        MissingFile = '._exception:MissingFile',
        MissingDirectory = '._exception:MissingDirectory',
    )
))
