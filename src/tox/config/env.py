from __future__ import absolute_import, unicode_literals

import sys

import py

import tox


class TestenvConfig(object):
    """Testenv Configuration object.

    In addition to some core attributes/properties this config object holds all
    per-testenv ini attributes as attributes, see "tox --help-ini" for an overview.
    """

    def __init__(self, envname, config, factors, reader):
        #: test environment name
        self.envname = envname
        #: global tox config object
        self.config = config
        #: set of factors
        self.factors = factors
        self._reader = reader
        self.missing_subs = []
        """Holds substitutions that could not be resolved.

        Pre 2.8.1 missing substitutions crashed with a ConfigError although this would not be a
        problem if the env is not part of the current test run. So we need to remember this and
        check later when the test env is actually run and crash only then.
        """

    def get_envbindir(self):
        """Path to directory where scripts/binaries reside."""
        if self.host_env is True:
            return py.path.local(py.path.local(sys.executable).dirname)
        if tox.INFO.IS_WIN and "jython" not in self.basepython and "pypy" not in self.basepython:
            return self.envdir.join("Scripts")
        else:
            return self.envdir.join("bin")

    @property
    def envbindir(self):
        return self.get_envbindir()

    @property
    def envpython(self):
        """Path to python executable."""
        return self.get_envpython()

    def get_envpython(self):
        """ path to python/jython executable. """
        if "jython" in str(self.basepython):
            name = "jython"
        else:
            name = "python"
        return self.envbindir.join(name)

    def get_envsitepackagesdir(self):
        """Return sitepackagesdir of the virtualenv environment.

        NOTE: Only available during execution, not during parsing.
        """
        value = self.config.interpreters.get_sitepackagesdir(
            info=self.python_info, envdir=sys.prefix if self.host_env is True else self.envdir
        )
        return value

    @property
    def python_info(self):
        """Return sitepackagesdir of the virtualenv environment."""
        return self.config.interpreters.get_info(envconfig=self)

    def getsupportedinterpreter(self):
        if tox.INFO.IS_WIN and self.basepython and "jython" in self.basepython:
            raise tox.exception.UnsupportedInterpreter(
                "Jython/Windows does not support installing scripts"
            )
        info = self.config.interpreters.get_info(envconfig=self)
        if not info.executable:
            raise tox.exception.InterpreterNotFound(self.basepython)
        if not info.version_info:
            raise tox.exception.InvocationError(
                "Failed to get version_info for {}: {}".format(info.name, info.err)
            )
        return info.executable
