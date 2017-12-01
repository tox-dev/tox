Basic usage
=============================================

a simple tox.ini / default environments
-----------------------------------------------

Put basic information about your project and the test environments you
want your project to run in into a ``tox.ini`` file that should
reside next to your ``setup.py`` file:

.. code-block:: ini

    # content of: tox.ini , put in same dir as setup.py
    [tox]
    envlist = py27,py36
    [testenv]
    deps=pytest # or 'nose' or ...
    commands=pytest  # or 'nosetests' or ...

To sdist-package, install and test your project, you can
now type at the command prompt:

.. code-block:: shell

    tox

This will sdist-package your current project, create two virtualenv_
Environments, install the sdist-package into the environments and run
the specified command in each of them.  With:

.. code-block:: shell

    tox -e py36

you can run restrict the test run to the python3.6 environment.

Available "default" test environments names are:

.. code-block:: shell

    py
    py2
    py27
    py3
    py34
    py35
    py36
    py37
    jython
    pypy
    pypy3

The environment ``py`` uses the version of Python used to invoke tox.

However, you can also create your own test environment names,
see some of the examples in :doc:`examples <../examples>`.

specifying a platform
-----------------------------------------------

.. versionadded:: 2.0

If you want to specify which platform(s) your test environment
runs on you can set a platform regular expression like this:

.. code-block:: ini

    platform = linux2|darwin

If the expression does not match against ``sys.platform``
the test environment will be skipped.

whitelisting non-virtualenv commands
-----------------------------------------------

.. versionadded:: 1.5

Sometimes you may want to use tools not contained in your
virtualenv such as ``make``, ``bash`` or others. To avoid
warnings you can use the ``whitelist_externals`` testenv
configuration:

.. code-block:: ini

    # content of tox.ini
    [testenv]
    whitelist_externals = make
                          /bin/bash


.. _virtualenv: https://pypi.python.org/pypi/virtualenv

.. _multiindex:

depending on requirements.txt or defining constraints
-----------------------------------------------------

.. versionadded:: 1.6.1

(experimental) If you have a ``requirements.txt`` file or a ``constraints.txt`` file you can add it to your ``deps`` variable like this:

.. code-block:: ini

    deps = -rrequirements.txt

or

.. code-block:: ini

    deps = -cconstraints.txt

or

.. code-block:: ini

    deps = -rrequirements.txt -cconstraints.txt

All installation commands are executed using ``{toxinidir}`` (the directory where ``tox.ini`` resides) as the current working directory.
Therefore, the underlying ``pip`` installation will assume ``requirements.txt`` or ``constraints.txt`` to exist at ``{toxinidir}/requirements.txt`` or ``{toxinidir}/contrains.txt``.

This is actually a side effect that all elements of the dependency list is directly passed to ``pip``.

For more details on ``requirements.txt`` files or ``constraints.txt`` files please see:

* https://pip.pypa.io/en/stable/user_guide/#requirements-files
* https://pip.pypa.io/en/stable/user_guide/#constraints-files

using a different default PyPI url
-----------------------------------------------

.. versionadded:: 0.9

To install dependencies and packages from a different
default PyPI server you can type interactively:

.. code-block:: shell

    tox -i http://pypi.my-alternative-index.org

This causes tox to install dependencies and the sdist install step
to use the specificied url as the index server.

You can cause the same effect by this ``tox.ini`` content:

.. code-block:: ini

    [tox]
    indexserver =
        default = http://pypi.my-alternative-index.org

installing dependencies from multiple PyPI servers
---------------------------------------------------

.. versionadded:: 0.9

You can instrument tox to install dependencies from
different PyPI servers, example:

.. code-block:: ini

    [tox]
    indexserver =
        DEV = http://mypypiserver.org

    [testenv]
    deps =
        docutils        # comes from standard PyPI
        :DEV:mypackage  # will be installed from custom "DEV" pypi url

This configuration will install ``docutils`` from the default
Python PYPI server and will install the ``mypackage`` from
our ``DEV`` indexserver, and the respective ``http://mypypiserver.org``
url.  You can override config file settings from the command line
like this:

.. code-block:: shell

    tox -i DEV=http://pypi.python.org/simple  # changes :DEV: package URLs
    tox -i http://pypi.python.org/simple      # changes default

further customizing installation
---------------------------------

.. versionadded:: 1.6

By default tox uses `pip`_ to install packages, both the
package-under-test and any dependencies you specify in ``tox.ini``.
You can fully customize tox's install-command through the
testenv-specific :confval:`install_command=ARGV` setting.
For instance, to use pip's ``--find-links`` and ``--no-index`` options to specify
an alternative source for your dependencies:

.. code-block:: ini

    [testenv]
    install_command = pip install --pre --find-links http://packages.example.com --no-index {opts} {packages}

.. _pip: https://pip.pypa.io/en/stable/

forcing re-creation of virtual environments
-----------------------------------------------

.. versionadded:: 0.9

To force tox to recreate a (particular) virtual environment:

.. code-block:: shell

    tox --recreate -e py27

would trigger a complete reinstallation of the existing py27 environment
(or create it afresh if it doesn't exist).

passing down environment variables
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

setting environment variables
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

special handling of PYTHONHASHSEED
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

  Integrating tox with ``setup.py test`` is as of October 2016 discouraged as
  it breaks packaging/testing approaches as used by downstream distributions
  which expect ``setup.py test`` to run tests with the invocation interpreter
  rather than setting up many virtualenvs and installing packages.  If you need to
  define ``setup.py test`` you can better see about integrating your eventual
  test runner with it, here is an `example of setup.py test integration with pytest
  <https://docs.pytest.org/en/latest/goodpractices.html#integrating-with-setuptools-python-setup-py-test-pytest-runner>`_.
  As the python eco-system rather moves away from using ``setup.py`` as a tool entry
  point it's maybe best to not go for any ``setup.py test`` integration.



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
    envlist = py{27,34,36}-django{15,16}-{sqlite,mysql}

    [testenv]
    deps =
        django15: Django>=1.5,<1.6
        django16: Django>=1.6,<1.7
        py34-mysql: PyMySQL     ; use if both py34 and mysql are in an env name
        py27,py36: urllib3      ; use if any of py36 or py27 are in an env name
        py{27,36}-sqlite: mock  ; mocking sqlite in python 2.x

Prevent symbolic links in virtualenv
------------------------------------
By default virtualenv will use symlinks to point to the system's python files, modules, etc.
If you want the files to be copied instead, possibly because your filesystem is not capable
of handling symbolic links, you can instruct virtualenv to use the "--always-copy" argument
meant exactly for that purpose, by setting the ``alwayscopy`` directive in your environment:

.. code-block:: ini

    [testenv]
    alwayscopy = True
