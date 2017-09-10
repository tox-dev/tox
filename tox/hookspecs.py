""" Hook specifications for tox.

"""
from pluggy import HookimplMarker
from pluggy import HookspecMarker

hookspec = HookspecMarker("tox")
hookimpl = HookimplMarker("tox")


@hookspec
def tox_addoption(parser):
    """ add command line options to the argparse-style parser object."""


@hookspec
def tox_configure(config):
    """ called after command line options have been parsed and the ini-file has
    been read.  Please be aware that the config object layout may change as its
    API was not designed yet wrt to providing stability (it was an internal
    thing purely before tox-2.0). """


@hookspec(firstresult=True)
def tox_get_python_executable(envconfig):
    """ return a python executable for the given python base name.
    The first plugin/hook which returns an executable path will determine it.

    ``envconfig`` is the testenv configuration which contains
    per-testenv configuration, notably the ``.envname`` and ``.basepython``
    setting.
    """


@hookspec(firstresult=True)
def tox_testenv_create(venv, action):
    """ [experimental] perform creation action for this venv.

    Some example usage:

    - To *add* behavior but still use tox's implementation to set up a
      virtualenv, implement this hook but do not return a value (or explicitly
      return ``None``).
    - To *override* tox's virtualenv creation, implement this hook and return
      a non-``None`` value.

    .. note:: This api is experimental due to the unstable api of
        :class:`tox.venv.VirtualEnv`.

    .. note:: This hook uses ``firstresult=True`` (see pluggy_) -- hooks
        implementing this will be run until one returns non-``None``.

    .. _pluggy: http://pluggy.readthedocs.io/en/latest/#first-result-only
    """


@hookspec(firstresult=True)
def tox_testenv_install_deps(venv, action):
    """ [experimental] perform install dependencies action for this venv.

    Some example usage:

    - To *add* behavior but still use tox's implementation to install
      dependencies, implement this hook but do not return a value (or
      explicitly return ``None``).  One use-case may be to install (or ensure)
      non-python dependencies such as debian packages.
    - To *override* tox's installation of dependencies, implement this hook
      and return a non-``None`` value.  One use-case may be to install via
      a different installation tool such as `pip-accel`_ or `pip-faster`_.

    .. note:: This api is experimental due to the unstable api of
        :class:`tox.venv.VirtualEnv`.

    .. note:: This hook uses ``firstresult=True`` (see pluggy_) -- hooks
        implementing this will be run until one returns non-``None``.

    .. _pip-accel: https://github.com/paylogic/pip-accel
    .. _pip-faster: https://github.com/Yelp/venv-update
    .. _pluggy: http://pluggy.readthedocs.io/en/latest/#first-result-only
    """


@hookspec
def tox_runtest_pre(venv):
    """ [experimental] perform arbitrary action before running tests for this venv.

    This could be used to indicate that tests for a given venv have started, for instance.
    """


@hookspec(firstresult=True)
def tox_runtest(venv, redirect):
    """ [experimental] run the tests for this venv.

    .. note:: This hook uses ``firstresult=True`` (see pluggy_) -- hooks
        implementing this will be run until one returns non-``None``.
    """


@hookspec
def tox_runtest_post(venv):
    """ [experimental] perform arbitrary action after running tests for this venv.

    This could be used to have per-venv test reporting of pass/fail status.
    """
