.. be in -*- rst -*- mode!

tox plugins
===========

.. versionadded:: 2.0

A growing number of hooks make tox modifiable in different phases of execution by writing plugins.

tox - like `pytest`_ and `devpi`_ - uses `pluggy`_ to provide an extension mechanism for pip-installable internal or devpi/PyPI-published plugins.

Using plugins
-------------

To start using a plugin you need to install it in the same environment where the tox host
is installed.

e.g.:

.. code-block:: shell

    $ pip install tox-travis

You can search for available plugins on PyPI by visiting `PyPI <https://pypi.org/search/?q=tox>`_ and
searching for packages that are prefixed ``tox-`` or contain the word "plugin" in the description.
Examples include::

    tox-ansible                          - Plugin for generating tox environments for tools like ansible-test
    tox-asdf                             - A tox plugin that finds python executables using asdf
    tox-backticks                        - Allows backticks within setenv blocks for populating
                                           environment variables
    tox-bindep                           - Runs bindep checks prior to tests
    tox-bitbucket-status                 - Update bitbucket status for each env
    tox-cmake                            - Build CMake projects using tox
    tox-conda                            - Provides integration with the condo package manager
    tox-current-env                      - Run tests in the current python environment
    tox-docker                           - Launch a docker instance around test runs
    tox-direct                           - Run everything directly without tox venvs
    tox-envlist                          - Allows selection of a different tox envlist
    tox-envreport                        - A tox-plugin to document the setup of used virtual
    tox-factor                           - Runs a subset of tox test environments
    tox-globinterpreter                  - tox plugin to allow specification of interpreter
    tox-gh-actions                       - A plugin for helping to run tox in GitHub actions.
    tox-ltt                              - Light-the-torch integration
    tox-no-internet                      - Workarounds for using tox with no internet connection
    tox-pdm                              - Utilizes PDM as the package manager and installer
    tox-pip-extensions                   - Augment tox with different installation methods via
                                           progressive enhancement.
    tox-pipenv                           - A pipenv plugin for tox
    tox-pipenv-install                   - Install packages from Pipfile
    tox-poetry                           - Install packages using poetry
    tox-py-backwards                     - tox plugin for py-backwards
    tox-pyenv                            - tox plugin that makes tox use ``pyenv which`` to find
                                           python executables
    tox-pytest-summary                   - tox + Py.test summary
    tox-run-before                       - tox plugin to run shell commands before the test
                                           environments are created.
    tox-run-command                      - tox plugin to run arbitrary commands in a virtualenv
    tox-tags                             - Allows running subsets of environments based on tags
    tox-travis                           - Seamless integration of tox into Travis CI
    tox-venv                             - Use python3 venvs for python3 tox testenvs environments.
    tox-virtualenv-no-download           - Disable virtualenv's download-by-default in tox


There might also be some plugins not (yet) available from PyPI that could be installed directly
from source hosters like Github or Bitbucket (or from a local clone). See the associated `pip documentation <https://pip.pypa.io/en/stable/reference/pip_install/#vcs-support>`_.

To see what is installed you can call ``tox --version`` to get the version of the host and names
and locations of all installed plugins::

    3.0.0 imported from /home/ob/.virtualenvs/tmp/lib/python3.6/site-packages/tox/__init__.py
    registered plugins:
        tox-travis-0.10 at /home/ob/.virtualenvs/tmp/lib/python3.6/site-packages/tox_travis/hooks.py


Creating a plugin
-----------------

Start from a template

You can create a new tox plugin with all the bells and whistles via a `Cookiecutter`_ template
(see `cookiecutter-tox-plugin`_ - this will create a complete PyPI-releasable, documented
project with license, documentation and CI.

.. code-block:: shell

    $ pip install -U cookiecutter
    $ cookiecutter gh:tox-dev/cookiecutter-tox-plugin


Tutorial: a minimal tox plugin
------------------------------

.. note::

    This is the minimal implementation to demonstrate what is absolutely necessary to have a
    working plugin for internal use. To move from something like this to a publishable plugin
    you could apply ``cookiecutter -f cookiecutter-tox-plugin`` and adapt the code to the
    package based structure used in the cookiecutter.

Let us consider you want to extend tox behaviour by displaying fireworks at the end of a
successful tox run (we won't go into the details of how to display fireworks though).

To create a working plugin you need at least a python project with a tox entry point and a python
module implementing one or more of the pluggy-based hooks tox specifies (using the
``@tox.hookimpl`` decorator as marker).

minimal structure:

.. code-block:: shell

    $ mkdir tox-fireworks
    $ cd tox-fireworks
    $ touch tox_fireworks.py
    $ touch setup.py

contents of ``tox_fireworks.py``:

.. code-block:: python

    import pluggy

    hookimpl = pluggy.HookimplMarker("tox")


    @hookimpl
    def tox_addoption(parser):
        """Add command line option to display fireworks on request."""


    @hookimpl
    def tox_configure(config):
        """Post process config after parsing."""


    @hookimpl
    def tox_runenvreport(config):
        """Display fireworks if all was fine and requested."""

.. note::

    See :ref:`toxHookSpecsApi` for details

contents of ``setup.py``:

.. code-block:: python

    from setuptools import setup

    setup(
        name="tox-fireworks",
        py_modules=["tox_fireworks"],
        entry_points={"tox": ["fireworks = tox_fireworks"]},
        classifiers=["Framework:: tox"],
    )

Using the  **tox-** prefix in ``tox-fireworks`` is an established convention to be able to
see from the project name that this is a plugin for tox. It also makes it easier to find with
e.g. ``pip search 'tox-'`` once it is released on PyPI.

To make your new plugin discoverable by tox, you need to install it. During development you should
install it with ``-e`` or ``--editable``, so that changes to the code are immediately active:

.. code-block:: shell

    $ pip install -e </path/to/tox-fireworks>


Publish your plugin to PyPI
---------------------------

If you think the rest of the world could profit using your plugin, you can publish it to PyPI.

You need to add some more meta data to ``setup.py`` (see `cookiecutter-tox-plugin`_ for a complete
example or consult the `setup.py docs <https://docs.python.org/3/distutils/setupscript.html>`_).


.. note::

    Make sure your plugin project name is prefixed by ``tox-`` to be easy to find via e.g.
    ``pip search tox-``

You can and publish it like:

.. code-block:: shell

    $ cd </path/to/tox-fireworks>
    $ python setup.py sdist bdist_wheel upload

.. note::

    You could also use `twine <https://pypi.org/project/twine/>`_ for secure uploads.

    For more information about packaging and deploying Python projects see the
    `Python Packaging Guide`_.

.. _toxHookSpecsApi:


Hook specifications and related API
-----------------------------------

.. automodule:: tox.hookspecs
    :members:

.. autoclass:: tox.config.Parser()
    :members:

.. autoclass:: tox.config.Config()
    :members:

.. autoclass:: tox.config.TestenvConfig()
    :members:

.. autoclass:: tox.venv.VirtualEnv()
    :members:

.. autoclass:: tox.session.Session()
    :members:

.. include:: links.rst
