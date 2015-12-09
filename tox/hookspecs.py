""" Hook specifications for tox.

"""

from pluggy import HookspecMarker, HookimplMarker

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


@hookspec
def tox_testenv_create(venv, action):
    """ [experimental] perform creation action for this venv.
    """


@hookspec
def tox_testenv_install_deps(venv, action):
    """ [experimental] perform install dependencies action for this venv.  """
