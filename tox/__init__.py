#
__version__ = "0.5dev"

import apipkg

apipkg.initpkg(__name__, dict(
    cmdline   = '._cmdline:main',
    exception = dict(
        ConfigError = '._config:ConfigError',
        InvocationError = '._cmdline:InvocationError',
        MissingInterpreter = '._venv:MissingInterpreter',
    )
))
