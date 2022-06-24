Basic usage
=============================================

A simple tox.ini / default environments
-----------------------------------------------

Put basic information about your project and the test environments you
want your project to run in into a ``tox.ini`` file that should
reside next to your ``setup.py`` file:

.. code-block:: ini

    # content of: tox.ini , put in same dir as setup.py
    [tox]
    envlist = py27,py36
    [testenv]
    # install testing framework
    # ... or install anything else you might need here
    deps = pytest
    # run the tests
    # ... or run any other command line tool you need to run here
    commands = pytest

To sdist-package, install and test your project, you can
now type at the command prompt:

.. code-block:: shell

    tox

This will sdist-package your current project, create two virtualenv_
Environments, install the sdist-package into the environments and run
the specified command in each of them.  With:

.. code-block:: shell

    tox -e py36

you can restrict the test run to the python3.6 environment.

Tox currently understands the following patterns:

.. code-block:: shell

    py: The current Python version tox is using
    pypy: Whatever available PyPy there is
    jython: Whatever available Jython there is
    pyN: Python of version N. for example py2 or py3 ... etc
    pyNM: Python of version N.M. for example py27 or py38 ... etc
    pypyN: PyPy of version N. for example pypy2 or pypy3 ... etc
    pypyNM: PyPy version N.M. for example pypy27 or pypy35 ... etc

However, you can also create your own test environment names,
see some of the examples in :doc:`examples <../examples>`.

pyproject.toml tox legacy ini
-----------------------------

The tox configuration can also be in ``pyproject.toml`` (if you want to avoid an extra file).

Currently only the old format is supported via ``legacy_tox_ini``, a native implementation is planned though.

.. code-block:: toml

   [build-system]
   requires = [ "setuptools >= 35.0.2", "wheel >= 0.29.0"]
   build-backend = "setuptools.build_meta"

   [tool.tox]
   legacy_tox_ini = """
   [tox]
   envlist = py27,py36

   [testenv]
   deps = pytest >= 3.0.0, <4
   commands = pytest
   """

Note that when you define a ``pyproject.toml`` you must define the ``build-system`` section per PEP-518.

Specifying a platform
-----------------------------------------------

.. versionadded:: 2.0

If you want to specify which platform(s) your test environment
runs on you can set a platform regular expression like this:

.. code-block:: ini

    [testenv]
    platform = linux2|darwin

If the expression does not match against ``sys.platform``
the test environment will be skipped.

Allowing non-virtualenv commands
-----------------------------------------------

.. versionadded:: 1.5

Sometimes you may want to use tools not contained in your
virtualenv such as ``make``, ``bash`` or others. To avoid
warnings you can use the ``allowlist_externals`` testenv
configuration:

.. code-block:: ini

    # content of tox.ini
    [testenv]
    allowlist_externals = make
                          /bin/bash


.. _virtualenv: https://pypi.org/project/virtualenv

.. _multiindex:

Depending on requirements.txt or defining constraints
-----------------------------------------------------

.. versionadded:: 1.6.1

(experimental) If you have a ``requirements.txt`` file you can add it to your ``deps`` variable like this:

.. code-block:: ini

    [testenv]
    deps = -rrequirements.txt

This is actually a side effect that all elements of the dependency list is directly passed to ``pip``.

If you have a ``constraints.txt`` file you could add it to your ``deps`` like the ``requirements.txt`` file above.
However, then it would not be applied to

* build time dependencies when using isolated builds (https://github.com/pypa/pip/issues/8439)
* run time dependencies not already listed in ``deps``.

A better method may be to use ``setenv`` like this:

.. code-block:: ini

    [testenv]
    setenv = PIP_CONSTRAINT=constraints.txt

Make sure that all dependencies, including transient dependencies, are listed in your ``constraints.txt`` file or the version used may vary.

It should be noted that ``pip``, ``setuptools`` and ``wheel`` are often not part of the dependency tree and will be left at whatever version ``virtualenv`` used to seed the environment.

All installation commands are executed using ``{toxinidir}`` (the directory where ``tox.ini`` resides) as the current working directory.
Therefore, the underlying ``pip`` installation will assume ``requirements.txt`` or ``constraints.txt`` to exist at ``{toxinidir}/requirements.txt`` or ``{toxinidir}/constraints.txt``.


For more details on ``requirements.txt`` files or ``constraints.txt`` files please see:

* https://pip.pypa.io/en/stable/user_guide/#requirements-files
* https://pip.pypa.io/en/stable/user_guide/#constraints-files

Using a different default PyPI URL
----------------------------------

To install dependencies and packages from a different
default PyPI server you can type interactively:

.. code-block:: shell

    tox -i https://pypi.my-alternative-index.org

This causes tox to install dependencies and the sdist install step
to use the specified URL as the index server.

You can cause the same effect by using a ``PIP_INDEX_URL`` environment variable.
This variable can be also set in ``tox.ini``:

.. code-block:: ini

    [testenv]
    setenv =
        PIP_INDEX_URL = https://pypi.my-alternative-index.org

Alternatively, a configuration where ``PIP_INDEX_URL`` could be overridden from environment:

.. code-block:: ini

    [testenv]
    setenv =
        PIP_INDEX_URL = {env:PIP_INDEX_URL:https://pypi.my-alternative-index.org}

Installing dependencies from multiple PyPI servers
--------------------------------------------------

You can instrument tox to install dependencies from
multiple PyPI servers, using ``PIP_EXTRA_INDEX_URL`` environment variable:

.. code-block:: ini

    [testenv]
    setenv =
        PIP_EXTRA_INDEX_URL = https://mypypiserver.org
    deps =
        # docutils will be installed directly from PyPI
        docutils
        # mypackage missing at PyPI will be installed from custom PyPI URL
        mypackage

This configuration will install ``docutils`` from the default
Python PyPI server and will install the ``mypackage`` from
our index server at ``https://mypypiserver.org`` URL.

.. warning::

  Using an extra PyPI index for installing private packages may cause security issues.
  For example, if ``mypackage`` is registered with the default PyPI index, pip will install ``mypackage``
  from the default PyPI index, not from the custom one.

Further customizing installation
---------------------------------

.. versionadded:: 1.6

By default tox uses `pip`_ to install packages, both the
package-under-test and any dependencies you specify in ``tox.ini``.
You can fully customize tox's install-command through the
testenv-specific :conf:`install_command = ARGV <install_command>` setting.
For instance, to use pip's ``--find-links`` and ``--no-index`` options to specify
an alternative source for your dependencies:

.. code-block:: ini

    [testenv]
    install_command = pip install --pre --find-links https://packages.example.com --no-index {opts} {packages}

.. _pip: https://pip.pypa.io/en/stable/

Forcing re-creation of virtual environments
-----------------------------------------------

.. versionadded:: 0.9

To force tox to recreate a (particular) virtual environment:

.. code-block:: shell

    tox --recreate -e py27

would trigger a complete reinstallation of the existing py27 environment
(or create it afresh if it doesn't exist).

Passing down environment variables
-------------------------------------------

.. versionadded:: 2.0

By default tox will only pass the ``PATH`` environment variable (and on
windows ``SYSTEMROOT`` and ``PATHEXT``) from the tox invocation to the
test environments.  If you want to pass down additional environment
variables you can use the ``passenv`` option:

.. code-block:: ini

    [testenv]
    passenv = LANG

When your test commands execute they will execute with
the same LANG setting as the one with which tox was invoked.

Setting environment variables
-------------------------------------------

.. versionadded:: 1.0

If you need to set an environment variable like ``PYTHONPATH`` you
can use the ``setenv`` directive:

.. code-block:: ini

    [testenv]
    setenv = PYTHONPATH = {toxinidir}/subdir

When your test commands execute they will execute with
a PYTHONPATH setting that will lead Python to also import
from the ``subdir`` below the directory where your ``tox.ini``
file resides.

Special handling of PYTHONHASHSEED
-------------------------------------------

.. versionadded:: 1.6.2

By default, tox sets PYTHONHASHSEED_ for test commands to a random integer
generated when ``tox`` is invoked.  This mimics Python's hash randomization
enabled by default starting `in Python 3.3`_.  To aid in reproducing test
failures, tox displays the value of ``PYTHONHASHSEED`` in the test output.

You can tell tox to use an explicit hash seed value via the ``--hashseed``
command-line option to ``tox``.  You can also override the hash seed value
per test environment in ``tox.ini`` as follows:

.. code-block:: ini

    [testenv]
    setenv = PYTHONHASHSEED = 100

If you wish to disable this feature, you can pass the command line option
``--hashseed=noset`` when ``tox`` is invoked. You can also disable it from the
``tox.ini`` by setting ``PYTHONHASHSEED = 0`` as described above.

.. _`in Python 3.3`: https://docs.python.org/3/whatsnew/3.3.html#builtin-functions-and-types
.. _PYTHONHASHSEED: https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED

Integration with "setup.py test" command
----------------------------------------------------

.. warning::

  ``setup.py test`` is `deprecated
  <https://setuptools.readthedocs.io/en/latest/setuptools.html#test-build-package-and-run-a-unittest-suite>`_
  and will be removed in a future version.

.. _`ignoring exit code`:

Ignoring a command exit code
----------------------------

In some cases, you may want to ignore a command exit code. For example:

.. code-block:: ini

    [testenv:py27]
    commands = coverage erase
           {envbindir}/python setup.py develop
           coverage run -p setup.py test
           coverage combine
           - coverage html
           {envbindir}/flake8 loads

By using the ``-`` prefix, similar to a ``make`` recipe line, you can ignore
the exit code for that command.

Compressing dependency matrix
-----------------------------

If you have a large matrix of dependencies, python versions and/or environments you can
use :ref:`generative-envlist` and :ref:`conditional settings <factors>` to express that in a concise form:

.. code-block:: ini

    [tox]
    envlist = py{36,37,38}-django{22,30}-{sqlite,mysql}

    [testenv]
    deps =
        django22: Django>=2.2,<2.3
        django30: Django>=3.0,<3.1
        # use PyMySQL if factors "py37" and "mysql" are present in env name
        py38-mysql: PyMySQL
        # use urllib3 if any of "py36" or "py37" are present in env name
        py36,py37: urllib3
        # mocking sqlite on 3.6 and 3.7 if factor "sqlite" is present
        py{36,37}-sqlite: mock


Using generative section names
------------------------------

Suppose you have some binary packages, and need to run tests both in 32 and 64 bits.
You also want an environment to create your virtual env for the developers.

.. code-block:: ini

    [testenv]
    basepython =
        py38-x86: python3.8-32
        py38-x64: python3.8-64
    commands = pytest

    [testenv:py38-{x86,x64}-venv]
    usedevelop = true
    envdir =
        x86: .venv-x86
        x64: .venv-x64
    commands =


Prevent symbolic links in virtualenv
------------------------------------
By default virtualenv will use symlinks to point to the system's python files, modules, etc.
If you want the files to be copied instead, possibly because your filesystem is not capable
of handling symbolic links, you can instruct virtualenv to use the "--always-copy" argument
meant exactly for that purpose, by setting the ``alwayscopy`` directive in your environment:

.. code-block:: ini

    [testenv]
    alwayscopy = True

.. _`parallel_mode`:

Parallel mode
-------------
``tox`` allows running environments in parallel:

- Invoke by using the ``--parallel`` or ``-p`` flag. After the packaging phase completes tox will run in parallel
  processes tox environments (spins a new instance of the tox interpreter, but passes through all host flags and
  environment variables).
- ``-p`` takes an argument specifying the degree of parallelization, defaulting to ``auto``:

  - ``all`` to run all invoked environments in parallel,
  - ``auto`` to limit it to CPU count,
  - or pass an integer to set that limit.
- Parallel mode displays a progress spinner while running tox environments in parallel, and reports outcome of
  these as soon as completed with a human readable duration timing attached. This spinner can be disabled by
  setting the environment variable ``TOX_PARALLEL_NO_SPINNER`` to the value ``1``.
- Parallel mode by default shows output only of failed environments and ones marked as :conf:`parallel_show_output`
  ``=True``.
- There's now a concept of dependency between environments (specified via :conf:`depends`), tox will re-order the
  environment list to be run to satisfy these dependencies (in sequential run too). Furthermore, in parallel mode,
  will only schedule a tox environment to run once all of its dependencies finished (independent of their outcome).

  .. warning::

    ``depends`` does not pull in dependencies into the run target, for example if you select ``py27,py36,coverage``
    via the ``-e`` tox will only run those three (even if ``coverage`` may specify as ``depends`` other targets too -
    such as ``py27, py35, py36, py37``).

- ``--parallel-live``/``-o`` allows showing the live output of the standard output and error, also turns off reporting
  described above.
- Note: parallel evaluation disables standard input. Use non parallel invocation if you need standard input.

Example final output:

.. code-block:: bash

    $ tox -e py27,py36,coverage -p all
    ✔ OK py36 in 9.533 seconds
    ✔ OK py27 in 9.96 seconds
    ✔ OK coverage in 2.0 seconds
    ___________________________ summary ______________________________________________________
      py27: commands succeeded
      py36: commands succeeded
      coverage: commands succeeded
      congratulations :)


Example progress bar, showing a rotating spinner, the number of environments running and their list (limited up to \
120 characters):

.. code-block:: bash

    ⠹ [2] py27 | py36

.. _`auto-provision`:

tox auto-provisioning
---------------------
In case the host tox does not satisfy either the :conf:`minversion` or the :conf:`requires`, tox will now automatically
create a virtual environment under :conf:`provision_tox_env` that satisfies those constraints and delegate all calls
to this meta environment. This should allow automatically satisfying constraints on your tox environment,
given you have at least version ``3.8.0`` of tox.

For example given:

.. code-block:: ini

    [tox]
    minversion = 3.10.0
    requires = tox_venv >= 1.0.0

if the user runs it with tox ``3.8.0`` or later installed tox will automatically ensured that both the minimum version
and requires constraints are satisfied, by creating a virtual environment under ``.tox`` folder, and then installing
into it ``tox >= 3.10.0`` and ``tox_venv >= 1.0.0``. Afterwards all tox invocations are forwarded to the tox installed
inside ``.tox\.tox`` folder (referred to as meta-tox or auto-provisioned tox).

This allows tox to automatically setup itself with all its plugins for the current project.  If the host tox satisfies
the constraints expressed with the :conf:`requires` and :conf:`minversion` no such provisioning is done (to avoid
setup cost when it's not explicitly needed).
