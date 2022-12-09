FAQ
===

Here you'll find answers to some frequently asked questions.

Breaking changes in tox 4
-------------------------
Version 4 of tox should be mostly backwards compatible with version 3, with the following exceptions:

tox 4 - Python support
++++++++++++++++++++++
- tox now requires Python ``3.7`` or later and is tested only against CPython. You can still create test environments
  for earlier Python versions or different Python interpreters. PyPy support is best effort, meaning we do not test it
  as part of our CI runs, however if you discover issues under PyPy we will accept PRs addressing it.

tox 4 - changed INI rules
+++++++++++++++++++++++++
- The hash sign (``#``) now always acts as comment within ``tox.ini`` or ``setup.cfg`` tox configuration file. Where you
  need to pass on a ``#`` character you will need to escape it in form of ``\#`` so tox does not handle everything right
  of the ``#`` character as a comment. Valid in tox 3:

  .. code-block:: ini

      # valid in tox 3
      commands = bash -c "echo 'foo#bar'"

      # valid in tox 4
      commands = bash -c "echo 'foo\#bar'"

- Within the ``pass_env`` you can no longer use space as value separator, instead you need to use the ``,`` or the
  newline character. This is to have the same value separation rules for all tox configuration lines.

  .. code-block:: ini

      # valid in tox 3
      passenv = ALPHA BETA
      passenv =
          ALPHA
          BETA

      # valid in tox 4
      passenv = ALPHA, BETA
      passenv =
          ALPHA
          BETA

- tox 4 now errors when using the ``-U`` flag when defining dependencies, e.g. ``deps = -Ur requirements.txt``. While
  this worked in tox 3, it was never supported officially. Additionally, in the context of a new virtual environment
  this flag makes no sense anyway.

tox 4 - known regressions
+++++++++++++++++++++++++

- With tox 4 the tty trait of the caller environment is no longer passed through. The most notable impact of this is
  that some tools no longer print colored output. A PR to address this is welcomed, in the meantime you can use the
  ``tty`` substitution to force color mode for these tools, see for example tox itself with pytest and mypy
  `here in tox.ini <https://github.com/tox-dev/tox/blob/main/tox.ini#L28>`_.

tox 4 - new plugin system
+++++++++++++++++++++++++

tox 4 is a grounds up rewrite of the code base, and while we kept the configuration layer compatibility no such effort
has been made for the programmatic API. Therefore, all plugins will need to redo their integration against the new code
base. If you're a plugin developer refer to the `plugin documentation <https://tox.wiki/en/latest/plugins.html>`_ for
more information.

tox 4 - removed tox.ini keys
++++++++++++++++++++++++++++

+--------------------------+---------------------------------------------+
| Configuration key        | Migration path                              |
+==========================+=============================================+
| ``indexserver``          | See `Using a custom PyPI server`_.          |
+--------------------------+---------------------------------------------+
| ``whitelist_externals``  | Use :ref:`allowlist_externals` key instead. |
+--------------------------+---------------------------------------------+
| ``isolated_build``       | Isolated builds are now always used.        |
+--------------------------+---------------------------------------------+

tox 4 - substitutions removed
+++++++++++++++++++++++++++++
- The ``distshare`` substitution has been removed.

tox 4 - disallowed env names
++++++++++++++++++++++++++++
- Environment names that contain multiple Python variants, such as ``name-py39-pypy`` or ``py39-py310`` will now raise
  an error, previously this only warned, you can use :ref:`ignore_basepython_conflict` to disable this error, but we
  recommend changing the name to avoid this name that can be confusing.

tox 4 - CLI arguments changed
+++++++++++++++++++++++++++++
- The ``--parallel--safe-build`` CLI argument has been removed, no longer needed.
- When you want to pass an option to a test command, e.g. to ``pytest``, now you must use ``--`` as a separator, this
  worked with version 3 also, but any unknown trailing arguments were automatically passed through, while now this is
  no longer the case.
- Running ``--showconfig```or ``--help-ini`` with the ``-v`` flag will add interleaved debugging information, whereas
  tox 3 added additional lines at the start. If you want to generate valid ini files you must not use the ``-v`` flag.

tox 4 - packaging changes
+++++++++++++++++++++++++
- We use isolated builds (always) as specified by :pep:`518` and use :pep:`517` to communicate with the build backend.
- The ``--develop`` CLI flag or the :ref:`use_develop` settings now enables editable installations via the :pep:`660`
  mechanism rather than the legacy ``pip install -e`` behaviour. The old functionality can still be forced by setting
  the :ref:`package` setting for the run environment to ``editable-legacy``.

tox 4 -- output changes
+++++++++++++++++++++++
- We now use colors for reporting, to help make the output easier to read for humans. This can be disabled via the
  ``TERM=dumb`` or ``NO_COLOR=1`` environment variables, or the ``--colored no`` CLI argument.

New features in tox 4
---------------------
Here is a non-exhaustive list of these.

- You can now build wheel(s) instead of a source distribution during the packaging phase by using the ``wheel`` setting
  for the :ref:`package` setting. If your package is a universal wheel you'll likely want to set the
  :ref:`wheel_build_env` to ``.pkg`` to avoid building a wheel for every Python version you target.
- Editable wheel support was added as defined by :pep:`660` via the :ref:`package` setting to ``editable``.
- We redesigned our CLI interface, we no longer try to squeeze everything under single command, instead now we have
  multiple sub-commands. For backwards compatibility if you do not specify a subcommand we'll assume you want the tox 3
  legacy interface (available under the legacy subcommand), for now the list of available commands are:

  .. code-block:: bash

    subcommands:
      tox command to execute (by default legacy)

      {run,r,run-parallel,p,depends,de,list,l,devenv,d,config,c,quickstart,q,exec,e,legacy,le}
        run (r)                   run environments
        run-parallel (p)          run environments in parallel
        depends (de)              visualize tox environment dependencies
        list (l)                  list environments
        devenv (d)                sets up a development environment at ENVDIR based on the tox configuration specified
        config (c)                show tox configuration
        quickstart (q)            Command line script to quickly create a tox config file for a Python project
        exec (e)                  execute an arbitrary command within a tox environment
        legacy (le)               legacy entry-point command

  The ``exec`` and ``depends`` are brand new features. Other subcommands are a more powerful versions of previously
  existing single flags (e.g. ``-av`` is now succeeded by the ``list`` subcommand). All subcommands have a one or two
  character shortcuts for less typing on the CLI (e.g. ``tox run`` can be abbreviated to ``tox r``). For more details
  see :ref:`cli`.
- Startup times should be improved because now we no longer eagerly load all configurations for all environments, but
  instead these are performed lazily when needed. Side-effect of this is that if you have an invalid configuration will
  not be picked up until you try to use it.
- We now discover your package dependency changes (either via :pep:`621` or otherwise via :pep:`517`
  ``prepare_metadata_for_build_wheel``/``build_wheel`` metadata). If new dependencies are added these will be installed
  on the next run. If a dependency is removed we'll recreate the entire environment. This works for ``requirements``
  files within the :ref:`deps`. This means that you should never need to use ``--recreate`` flag, tox should be smart
  enough to figure out when things change and automatically apply it.
- All tox defaults can now be changed via the user level config-file (see help message output for its location, can be
  changed via ``TOX_CONFIG_FILE`` environment variable).
- All tox defaults can now be changed via an environment variable: ``TOX_`` prefix followed by the settings key,
  e.g. ``TOX_PACKAGE=wheel``.
- Any configuration can be overwritten via the CLI ``-x`` or ``--override`` flag, e.g.
  ``tox run -e py311  -x testenv:py310.package=editable`` would force the packaging of environment ``py311`` to be an
  editable install independent what's in the configuration file.
- :ref:`basepython` is now a list, the first successfully detected python will be used to generate python environment.
- We now have support for inline tox plugins via the ``toxfile.py`` at the root of your project. At a later time this
  will allow using Python only configuration, as seen with nox.
- You can now group tox environments via :ref:`labels` configuration, and you can invoke all tox environments within a
  label by using the ``-m label`` CLI flag (instead of the ``-e list_of_envs``).
- You can now invoke all tox environments within a given factor via the ``-f factor`` CLI flag.

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

Customizing virtual environment creation
----------------------------------------

By default tox uses the :pypi:`virtualenv` to create Python virtual environments to run your tools in. To change how tox
creates virtual environments you can set environment variables to customize virtualenv. For example, to provision a given
pip version in the virtual environment you can set ``VIRTUALENV_PIP`` or to enable system site packages use the
``VIRTUALENV_SYSTEM_SITE_PACKAGES``:


.. code-block:: ini


   [testenv]
   setenv =
     VIRTUALENV_PIP==22.1
     VIRTUALENV_SYSTEM_SITE_PACKAGES=true

Consult the :pypi:`virtualenv` project for supported values (any CLI flag for virtualenv, in all upper case, prefixed
by the ``VIRTUALENV_`` key).

Building documentation with Sphinx
----------------------------------

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

Note here we also require Python 3.10, allowing us to use f-strings within the sphinx ``conf.py``.

Building documentation with mkdocs
----------------------------------

It's possible to orchestrate the projects documentation with tox. The advantage of this is that now generating the
documentation can be part of the CI, and whenever any validations/checks/operations fail while generating the
documentation you'll catch it within tox.

It's best to define one environment to write/generate the documentation, and another to deploy it. Use the config
substitution logic to avoid duplication:

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
:pypi:`pytest` you'd read `here <https://docs.pytest.org/en/latest/reference/exit-codes.html#exit-codes>`_. On unix
systems, there are some rather `common exit codes <http://www.faqs.org/docs/abs/HTML/exitcodes.html>`_. This is why for
exit codes larger than 128, if a signal with number equal to ``<exit code> - 128`` is found in the :py:mod:`signal`
module, an additional hint is given:

.. code-block:: shell

    ERROR: InvocationError for command
           '<command>' (exited with code 139)
    Note: this might indicate a fatal error signal (139 - 128 = 11: SIGSEGV)


The signal numbers (e.g. 11 for a segmentation fault) can be found in the "Standard signals" section of the
`signal man page <https://man7.org/linux/man-pages/man7/signal.7.html>`_.
Their meaning is described in `POSIX signals <https://en.wikipedia.org/wiki/Signal_(IPC)#POSIX_signals>`_. Beware
that programs may issue custom exit codes with any value, so their documentation should be consulted.


Sometimes, no exit code is given at all. An example may be found in
:gh:`pytest-qt issue #170 <pytest-dev/pytest-qt/issues/170>`, where Qt was calling
`abort() <https://www.unix.org/version2/sample/abort.html>`_ instead of ``exit()``.

Access full logs
----------------

If you want to access the full logs you need to write ``-q`` and ``-v`` as
individual tox arguments and avoid combining them into a single one.
