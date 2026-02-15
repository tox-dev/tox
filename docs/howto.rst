.. _howto:

How-to Guides
=============

Practical recipes for common tox tasks. Each section answers a specific "How do I...?" question.

.. _howto_custom_pypi_server:
.. _faq_custom_pypi_server:

How to use a custom PyPI server
-------------------------------

By default tox uses pip to install Python dependencies. To change the index server, configure pip directly via
environment variables:

.. tab:: TOML

   .. code-block:: toml

        [env_run_base]
        set_env = { PIP_INDEX_URL = "https://my.pypi.example/simple" }

   To allow the user to override the index server (e.g. for offline use), use substitution with a default:

   .. code-block:: toml

        [env_run_base]
        set_env = { PIP_INDEX_URL = { replace = "env", name = "PIP_INDEX_URL", default = "https://my.pypi.example/simple" } }

.. tab:: INI

   .. code-block:: ini

        [testenv]
        set_env =
            PIP_INDEX_URL = https://my.pypi.example/simple

   To allow the user to override the index server (e.g. for offline use), use substitution with a default:

   .. code-block:: ini

        [testenv]
        set_env =
            PIP_INDEX_URL = {env:PIP_INDEX_URL:https://my.pypi.example/simple}

How to use multiple PyPI servers
--------------------------------

When not all dependencies are found on a single index, use ``PIP_EXTRA_INDEX_URL``:

.. tab:: TOML

   .. code-block:: toml

        [env_run_base]
        set_env.PIP_INDEX_URL = { replace = "env", name = "PIP_INDEX_URL", default = "https://primary.example/simple" }
        set_env.PIP_EXTRA_INDEX_URL = { replace = "env", name = "PIP_EXTRA_INDEX_URL", default = "https://secondary.example/simple" }

.. tab:: INI

   .. code-block:: ini

        [testenv]
        set_env =
            PIP_INDEX_URL = {env:PIP_INDEX_URL:https://primary.example/simple}
            PIP_EXTRA_INDEX_URL = {env:PIP_EXTRA_INDEX_URL:https://secondary.example/simple}

If the index defined under ``PIP_INDEX_URL`` does not contain a package, pip will attempt to resolve it from
``PIP_EXTRA_INDEX_URL``.

.. warning::

   Using an extra PyPI index for installing private packages may cause security issues. If ``package1`` is
   registered with the default PyPI index, pip will install ``package1`` from the default PyPI index, not from the
   extra one.

How to use constraint files
----------------------------

`Constraint files <https://pip.pypa.io/en/stable/user_guide/#constraints-files>`_ define version constraints for
dependencies without specifying what to install. When creating a test environment, tox invokes pip multiple times:

1. If :ref:`deps` is specified, it installs those dependencies first.
2. If the environment has a package (not :ref:`package` ``skip`` or :ref:`skip_install` ``true``), it:

   1. Installs the package dependencies.
   2. Installs the package itself.

When ``constrain_package_deps = true`` is set, ``{env_dir}/constraints.txt`` is generated during ``install_deps``
based on the specifications in ``deps``. These constraints are then passed to pip during ``install_package_deps``,
raising an error when package dependencies conflict with test dependencies.

For stronger guarantees, set ``use_frozen_constraints = true`` to generate constraints from the exact installed
versions (via ``pip freeze``). This catches incompatibilities with any previously installed dependency.

.. note::

   Constraint files are a subset of requirement files. You can pass a constraint file wherever a requirement file is
   accepted.

.. _platform-specification:

How to configure platform-specific settings
--------------------------------------------

Use conditional factors to run different commands or dependencies per platform:

.. tab:: TOML

   .. code-block:: toml

        env_list = ["3.13-lin", "3.13-mac", "3.13-win"]

        [env_run_base]
        commands = [["python", "-c", "print('hello')"]]

.. tab:: INI

   .. code-block:: ini

        [tox]
        env_list = py{313}-{lin,mac,win}

        [testenv]
        platform = lin: linux
                   mac: darwin
                   win: win32

        deps = lin,mac: platformdirs==3
               win: platformdirs==2

        commands =
           lin: python -c 'print("Hello, Linus!")'
           mac: python -c 'print("Hello, Tim!")'
           win: python -c 'print("Hello, Satya!")'

The :ref:`platform` setting accepts a regular expression matched against ``sys.platform``. If it does not match, the
entire environment is skipped. Conditional factors (``lin:``, ``mac:``, ``win:``) filter individual settings.

.. note::

   Conditional factors and generative environments are currently only supported in the INI format.

How to ignore command exit codes
---------------------------------

When multiple commands are defined in :ref:`commands`, tox runs them sequentially and stops at the first failure
(non-zero exit code). To ignore the exit code of a specific command, prefix it with ``-``:

.. tab:: TOML

   .. code-block:: toml

        [env_run_base]
        commands = [
            ["-", "python", "-c", "import sys; sys.exit(1)"],
            ["python", "--version"],
        ]

.. tab:: INI

   .. code-block:: ini

        [testenv]
        commands =
            - python -c 'import sys; sys.exit(1)'
            python --version

To invert the exit code (fail if the command returns 0, succeed otherwise), use the ``!`` prefix:

.. tab:: TOML

   .. code-block:: toml

        [env_run_base]
        commands = [
            ["!", "python", "-c", "import sys; sys.exit(1)"],
            ["python", "--version"],
        ]

.. tab:: INI

   .. code-block:: ini

        [testenv]
        commands =
            ! python -c 'import sys; sys.exit(1)'
            python --version

How to customize virtualenv creation
--------------------------------------

tox uses :pypi:`virtualenv` to create Python virtual environments. Customize virtualenv behavior through
environment variables:

.. tab:: TOML

   .. code-block:: toml

        [env_run_base]
        set_env.VIRTUALENV_PIP = "22.1"
        set_env.VIRTUALENV_SYSTEM_SITE_PACKAGES = "true"

.. tab:: INI

   .. code-block:: ini

        [testenv]
        set_env =
            VIRTUALENV_PIP = 22.1
            VIRTUALENV_SYSTEM_SITE_PACKAGES = true

Any CLI flag for virtualenv can be set as an environment variable with the ``VIRTUALENV_`` prefix (in uppercase).
Consult the :pypi:`virtualenv` documentation for supported values.

How to build documentation with Sphinx
---------------------------------------

Orchestrate Sphinx documentation builds with tox to integrate them into CI:

.. tab:: TOML

   .. code-block:: toml

        [env.docs]
        description = "build documentation"
        deps = ["sphinx>=7"]
        commands = [
            ["sphinx-build", "-d", "{env_tmp_dir}/doctree", "docs", "{work_dir}/docs_out", "--color", "-b", "html"],
            ["python", "-c", "print(f'documentation available under file://{work_dir}/docs_out/index.html')"],
        ]

.. tab:: INI

   .. code-block:: ini

        [testenv:docs]
        description = build documentation
        deps =
            sphinx>=7
        commands =
            sphinx-build -d "{envtmpdir}{/}doctree" docs "{toxworkdir}{/}docs_out" --color -b html
            python -c 'print(r"documentation available under file://{toxworkdir}{/}docs_out{/}index.html")'

This approach avoids the platform-specific Makefile generated by Sphinx and works cross-platform.

How to build documentation with mkdocs
----------------------------------------

Define separate environments for developing and deploying mkdocs documentation:

.. tab:: TOML

   .. code-block:: toml

        [env.docs]
        description = "run a development server for documentation"
        deps = [
            "mkdocs>=1.3",
            "mkdocs-material",
        ]
        commands = [
            ["mkdocs", "build", "--clean"],
            ["python", "-c", "print('###### Starting local server. Press Control+C to stop ######')"],
            ["mkdocs", "serve", "-a", "localhost:8080"],
        ]

        [env.docs-deploy]
        description = "build and deploy documentation"
        deps = [
            "mkdocs>=1.3",
            "mkdocs-material",
        ]
        commands = [["mkdocs", "gh-deploy", "--clean"]]

.. tab:: INI

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

How to understand InvocationError exit codes
---------------------------------------------

When a command executed by tox fails, an ``InvocationError`` is raised:

.. code-block:: shell

    ERROR: InvocationError for command
           '<command defined in tox config>' (exited with code 1)

Always check the documentation for the command that failed. For example, for :pypi:`pytest`, see the
`pytest exit codes <https://docs.pytest.org/en/latest/reference/exit-codes.html#exit-codes>`_.

On Unix systems, exit codes larger than 128 indicate a fatal signal. tox provides a hint in these cases:

.. code-block:: shell

    ERROR: InvocationError for command
           '<command>' (exited with code 139)
    Note: this might indicate a fatal error signal (139 - 128 = 11: SIGSEGV)

Signal numbers are documented in the `signal man page <https://man7.org/linux/man-pages/man7/signal.7.html>`_.

How to access full logs
-----------------------

tox logs command invocations inside ``.tox/<env_name>/log``. Each execution is recorded in a file named
``<index>-<run_name>.log``, containing the command, environment variables, working directory, exit code, and output.

Environment variables with names containing sensitive words (``access``, ``api``, ``auth``, ``client``, ``cred``,
``key``, ``passwd``, ``password``, ``private``, ``pwd``, ``secret``, ``token``) are logged with their values redacted
to prevent accidental secret leaking.

How to run tox in Docker
-------------------------

The `31z4/tox <https://hub.docker.com/r/31z4/tox>`_ Docker image packages tox with common build dependencies and
`active CPython versions <https://devguide.python.org/versions/#status-of-python-versions>`_.

Mount your project directory as a volume:

.. code-block:: shell

    docker run -v `pwd`:/tests -it --rm 31z4/tox

Pass subcommands and flags directly:

.. code-block:: shell

    docker run -v `pwd`:/tests -it --rm 31z4/tox run-parallel -e lint,3.13

To add additional Python versions, create a derivative image:

.. code-block:: Dockerfile

    FROM 31z4/tox

    USER root
    RUN set -eux; \
        apt-get update; \
        DEBIAN_FRONTEND=noninteractive \
        apt-get install -y --no-install-recommends python3.14; \
        rm -rf /var/lib/apt/lists/*
    USER tox

.. _eol-version-support:

How to test end-of-life Python versions
----------------------------------------

tox uses :pypi:`virtualenv` under the hood. Newer virtualenv versions drop support for older Python interpreters:

- `virtualenv 20.22.0 <https://virtualenv.pypa.io/en/latest/changelog.html#v20-22-0-2023-04-19>`_ dropped
  Python 3.6 and earlier
- `virtualenv 20.27.0 <https://virtualenv.pypa.io/en/latest/changelog.html#v20-27-0-2024-10-17>`_ dropped
  Python 3.7

To test against these versions, pin virtualenv:

.. tab:: TOML

   .. code-block:: toml

        requires = ["virtualenv<20.22.0"]

.. tab:: INI

   .. code-block:: ini

        [tox]
        requires = virtualenv<20.22.0

How to test with pytest
------------------------

A typical pytest configuration:

.. tab:: TOML

   .. code-block:: toml

        env_list = ["3.13", "3.12"]

        [env_run_base]
        deps = ["pytest>=8"]
        commands = [["pytest", { replace = "posargs", default = ["tests"], extend = true }]]

.. tab:: INI

   .. code-block:: ini

        [tox]
        env_list = 3.13, 3.12

        [testenv]
        deps = pytest>=8
        commands = pytest {posargs:tests}

When running tox in parallel mode, ensure each pytest invocation is fully isolated by setting a unique temporary
directory:

.. tab:: TOML

   .. code-block:: toml

        [env_run_base]
        commands = [["pytest", "--basetemp={env_tmp_dir}", { replace = "posargs", default = ["tests"], extend = true }]]

.. tab:: INI

   .. code-block:: ini

        [testenv]
        commands = pytest --basetemp="{env_tmp_dir}" {posargs:tests}

How to override configuration defaults
----------------------------------------

tox provides several ways to override configuration values without editing the configuration file.

**User-level configuration file**: tox reads a user-level config file whose location is shown in ``tox --help``.
The location can be changed via the ``TOX_CONFIG_FILE`` environment variable.

**Environment variables**: Any tox setting can be set via an environment variable with the ``TOX_`` prefix:

.. code-block:: bash

    # Use wheel packaging
    TOX_PACKAGE=wheel tox run -e 3.13

**CLI override**: The ``-x`` (or ``--override``) flag overrides any configuration value:

.. code-block:: bash

    # Force editable install for a specific environment
    tox run -e 3.13 -x "testenv:3.13.package=editable"

How to control color output
-----------------------------

tox uses colored output by default. To disable it, use any of these methods:

.. code-block:: bash

    # Via environment variable
    NO_COLOR=1 tox run

    # Via TERM
    TERM=dumb tox run

    # Via CLI flag
    tox run --colored no

How to handle env names that match subcommands
-----------------------------------------------

tox has built-in subcommands (``run``, ``list``, ``config``, etc.). If you have an environment name that matches a
subcommand, use the ``run`` subcommand explicitly:

.. code-block:: bash

    # This would be interpreted as "tox list", not "run the list environment"
    # tox -e list  # does NOT work as expected

    # Use the run subcommand explicitly
    tox run -e list

    # Or the short alias
    tox r -e list

How to disallow unlisted environments
--------------------------------------

By default, running ``tox -e <name>`` with an environment name not defined in the configuration still works -- tox
creates an environment with default settings. This can mask typos.

For example, given:

.. tab:: TOML

   .. code-block:: toml

        [env.unit]
        deps = ["pytest"]
        commands = [["pytest"]]

.. tab:: INI

   .. code-block:: ini

        [testenv:unit]
        deps = pytest
        commands = pytest

Running ``tox -e unt`` or ``tox -e unti`` would succeed without running any tests. An exception is made for
environments starting with ``py`` -- in the above example, ``tox -e py313`` would still work as intended.
