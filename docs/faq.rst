FAQ
===

Here you'll find answers to some frequently asked questions.

Using a custom PyPI server
--------------------------

By default tox uses pip to install Python dependencies. Therefore to change the index server you should configure pip
directly. pip accepts environment variables as configuration flags, therefore the easiest way to do this is to set the
``PIP_INDEX_URL`` environment variable:

.. code-block:: ini

  set_env =
    PIP_INDEX_URL = https://tox.wiki/pypi/simple

It's considered a best practice to allow the user to change the index server rather than hard code it, allowing them
to use for example a local cache when they are offline. Therefore, a better form of this would be:

.. code-block:: ini

  set_env =
    PIP_INDEX_URL = {env:PIP_INDEX_URL:https://tox.wiki/pypi/simple}

Here we use an environment substitution to set the index URL if not set by the user, but otherwise default to our target
URI.

Using two PyPI servers
----------------------

When you want to use two PyPI index servers because not all dependencies are found in either of them use the
``PIP_EXTRA_INDEX_URL`` environment variable:

.. code-block:: ini

  set_env =
    PIP_INDEX_URL = {env:PIP_INDEX_URL:https://tox.wiki/pypi/simple-first}
    PIP_EXTRA_INDEX_URL = {env:PIP_EXTRA_INDEX_URL:https://tox.wiki/pypi/simple-second}

If the index server defined under ``PIP_INDEX_URL`` does not contain a package, pip will attempt to resolve it also from
the URI from ``PIP_EXTRA_INDEX_URL``.

.. warning::

  Using an extra PyPI index for installing private packages may cause security issues. For example, if ``package1`` is
  registered with the default PyPI index, pip will install ``package1`` from the default PyPI index, not from the extra
  one.

Using constraint files
----------------------
`Constraint files <https://pip.pypa.io/en/stable/user_guide/#constraints-files>`_ are a type of artifact, supported by
pip, that define not what requirements to install but instead what version constraints should be applied for the
otherwise specified requirements. The constraint file must always be specified together with the requirement(s) to
install. While creating a test environment tox will invoke pip multiple times, in separate phases:

1. If :ref:`deps` is specified, it will install a set of dependencies before installing the package.
2. If the target environment contains a package (the project does not have :ref:`package` ``skip`` or
   :ref:`skip_install` is ``true``), it will:

   1. install the dependencies of the package.
   2. install the package itself.

Some solutions and their drawbacks:

- specify the constraint files within :ref:`deps` (these constraints will not be applied when installing package
  dependencies),
- use ``PIP_CONSTRAINT`` inside :ref:`set_env` (tox will not know about the content of the constraint file and such
  will not trigger a rebuild of the environment when its content changes),
- specify the constraint file by extending the :ref:`install_command` as in the following example
  (tox will not know about the content of the constraint file and such will not trigger a rebuild of the environment
  when its content changes).

.. code-block:: ini

    [testenv:py39]
    install_command = python -m pip install {opts} {packages} -c constraints.txt
    extras = test

Note constraint files are a subset of requirement files. Therefore, it's valid to pass a constraint file wherever you
can specify a requirement file.

.. _platform-specification:

Platform specification
----------------------

Assuming the following layout:

.. code-block:: shell

    tox.ini      # see below for content
    setup.py     # a classic distutils/setuptools setup.py file

and the following ``tox.ini`` content:

.. code-block:: ini

    [tox]
    min_version = 2.0  # platform specification support is available since version 2.0
    envlist = py{310,39}-{lin,mac,win}

    [testenv]
    # environment will be skipped if regular expression does not match against the sys.platform string
    platform = lin: linux
               mac: darwin
               win: win32

    # you can specify dependencies and their versions based on platform filtered environments
    deps = lin,mac: platformdirs==3
           win: platformdirs==2

    # upon tox invocation you will be greeted according to your platform
    commands=
       lin: python -c 'print("Hello, Linus!")'
       mac: python -c 'print("Hello, Tim!")'
       win: python -c 'print("Hello, Satya!")'

You can invoke ``tox`` in the directory where your ``tox.ini`` resides. ``tox`` creates two virtualenv environments
with the ``python3.10`` and ``python3.9`` interpreters, respectively, and will then run the specified command according
to platform you invoke ``tox`` at.

Ignoring the exit code of a given command
-----------------------------------------

When multiple commands are defined within the :ref:`commands` configuration field tox will run them sequentially until
one of them fails (by exiting with non zero exit code) or all of them are run. If you want to ignore the status code of
a given command add a ``-`` prefix to that line (similar syntax to how the GNU ``make`` handles this):

.. code-block:: ini


   [testenv]
   commands =
     - python -c 'import sys; sys.exit(1)'
     python --version

Customize virtual environment creation
--------------------------------------

By default tox uses the :pypi:`project` to create Python virtual environments to run your tools in. To change how tox
creates virtual environments set environment variables to customize virtualenv. For example, to provision a given
pip version in the virtual environment set ``VIRTUALENV_PIP`` or to enable system site packages use the
``VIRTUALENV_SYSTEM_SITE_PACKAGES``:


.. code-block:: ini


   [testenv]
   setenv =
     VIRTUALENV_PIP==22.1
     VIRTUALENV_SYSTEM_SITE_PACKAGES=true

Consult the :pypi:`virtualenv` project for supported values (any CLI flag for virtualenv, in all upper case, prefixed
by the ``VIRTUALENV_`` key).

Build documentation with Sphinx
-------------------------------

It's possible to orchestrate the projects documentation with tox. The advantage of this is that now generating the
documentation can be part of the CI, and whenever any validations/checks/operations fail while generating the
documentation you'll catch it within tox.

We don't recommend using the Make and Batch file generated by Sphinx, as this makes your documentation generation
platform specific. A better solution is to use tox to setup a documentation build environment and invoke sphinx inside
it. This solution is cross platform.

For example if the sphinx file structure is under the ``docs`` folder the following configuration will generate
the documentation under ``.tox/docs_out/index.html`` and print out a link to the generated documentation:

.. code-block:: ini

    [testenv:docs]
    description = build documentation
    basepython = python3.10
    deps =
      sphinx>=4
    commands =
      sphinx-build -d "{envtmpdir}{/}doctree" docs "{toxworkdir}{/}docs_out" --color -b html
      python -c 'print(r"documentation available under file://{toxworkdir}{/}docs_out{/}index.html")'

Note here we also require python 3.10, allowing us to use f-strings within the sphinx ``conf.py``.

Build documentation with mkdocs
-------------------------------

It's possible to orchestrate the projects documentation with tox. The advantage of this is that now generating the
documentation can be part of the CI, and whenever any validations/checks/operations fail while generating the
documentation you'll catch it within tox.

It's best to define one environment to write/generate the documentation, and another to deploy it. Use the config
substitution logic to avoid defining dependencies multiple time:

.. code-block:: ini

    [testenv:docs]
    description = Run a development server for working on documentation
    deps =
      mkdocs>=1.3
      mkdocs-material
    commands =
      mkdocs build --clean
      python -c 'print("###### Starting local server. Press Control+C to stop server ######")'
      mkdocs serve -a localhost:8080

    [testenv:docs-deploy]
    description = built fresh docs and deploy them
    deps = {[testenv:docs]deps}
    commands = mkdocs gh-deploy --clean

Understanding ``InvocationError`` exit codes
--------------------------------------------

When a command executed by tox fails, it always has a non-zero exit code and an ``InvocationError`` exception is
raised:

.. code-block:: shell

    ERROR: InvocationError for command
           '<command defined in tox.ini>' (exited with code 1)

Generally always check the documentation for the command executed to understand what the code means. For example for
:pypi:`pytest` you'd read `here <https://docs.pytest.org/en/latest/usage.html#possible-exit-codes>`_. On unix systems,
there are some rather `common exit codes <http://www.faqs.org/docs/abs/HTML/exitcodes.html>`_. This is why for exit
codes larger than 128, if a signal with number equal to ``<exit code> - 128`` is found in the :py:mod:`signal` module,
an additional hint is given:

.. code-block:: shell

    ERROR: InvocationError for command
           '<command>' (exited with code 139)
    Note: this might indicate a fatal error signal (139 - 128 = 11: SIGSEGV)


The signal numbers (e.g. 11 for a segmentation fault) can be found in the "Standard signals" section of the
`signal man page <http://man7.org/linux/man-pages/man7/signal.7.html>`_.
Their meaning is described in `POSIX signals <https://en.wikipedia.org/wiki/Signal_(IPC)#POSIX_signals>`_. Beware
that programs may issue custom exit codes with any value, so their documentation should be consulted.


Sometimes, no exit code is given at all. An example may be found in
:gh:`pytest-qt issue #170 <pytest-dev/pytest-qt/issues/170>`, where Qt was calling
`abort() <http://www.unix.org/version2/sample/abort.html>`_ instead of ``exit()``.
