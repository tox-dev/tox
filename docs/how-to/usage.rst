.. _howto:

###############
 How-to Guides
###############

Practical recipes for common tox tasks. Each section answers a specific "How do I...?" question.

*****************
 Quick reference
*****************

Common commands
===============

- Each tox subcommand has a 1 (or 2) letter shortcut, e.g. ``tox run`` = ``tox r``, ``tox config`` = ``tox c``.
- Run all default environments: ``tox`` (runs everything in :ref:`env_list`).
- Run a specific environment: ``tox run -e 3.13``.
- Run multiple environments: ``tox run -e lint,3.13`` (sequential, in order).
- Run environments in parallel: ``tox parallel -e 3.13,3.12`` (see :ref:`parallel_mode`).
- Run all environments matching a label: ``tox run -m test`` (see :ref:`labels`).
- Run all environments matching a factor: ``tox run -f django`` (runs all envs containing the ``django`` factor).
- Inspect configuration: ``tox config -e 3.13 -k pass_env``.
- Force recreation: ``tox run -e 3.13 -r``.

Environment variables
=====================

- View environment variables: ``tox c -e 3.13 -k set_env pass_env``.
- Pass through system environment variables: use :ref:`pass_env`.
- Set environment variables: use :ref:`set_env`.
- Setup commands: :ref:`commands_pre`. Teardown commands: :ref:`commands_post`.
- Change working directory: :ref:`change_dir` (affects install commands too if using relative paths).

Logging
=======

tox logs command invocations inside ``.tox/<env_name>/log``. Environment variables with names containing sensitive words
(``access``, ``api``, ``auth``, ``client``, ``cred``, ``key``, ``passwd``, ``password``, ``private``, ``pwd``,
``secret``, ``token``) are logged with their values redacted to prevent accidental secret leaking in CI/CD environments.

.. ------------------------------------------------------------------------------------------

.. Testing & Verification (most common workflows)

.. ------------------------------------------------------------------------------------------

******************
 Test with pytest
******************

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

***********************************************
 Collect coverage across multiple environments
***********************************************

A common pattern is running tests across several Python versions and combining coverage results. Use :ref:`depends` to
ensure coverage runs after all test environments:

.. tab:: TOML

    .. code-block:: toml

         env_list = ["3.13", "3.12", "coverage"]

         [env_run_base]
         deps = ["pytest", "coverage[toml]"]
         commands = [["coverage", "run", "-p", "-m", "pytest", "tests"]]

         [env.coverage]
         skip_install = true
         deps = ["coverage[toml]"]
         depends = ["3.*"]
         commands = [
             ["coverage", "combine"],
             ["coverage", "report", "--fail-under=80"],
         ]

.. tab:: INI

    .. code-block:: ini

         [tox]
         env_list = 3.13, 3.12, coverage

         [testenv]
         deps =
             pytest
             coverage[toml]
         commands = coverage run -p -m pytest tests

         [testenv:coverage]
         skip_install = true
         deps = coverage[toml]
         depends = 3.*
         commands =
             coverage combine
             coverage report --fail-under=80

The ``-p`` flag (parallel mode) creates separate ``.coverage.<hash>`` files per environment. ``coverage combine`` merges
them before generating the report.

.. _tox-exec:

**********************************
 Run a one-off command (tox exec)
**********************************

The ``tox exec`` subcommand runs an arbitrary command inside a tox environment without executing the configured
``commands``, ``commands_pre``, or ``commands_post``. It also skips package installation. Pass the command after ``--``:

.. code-block:: bash

    # Open a Python shell inside the "3.13" environment
    tox exec -e 3.13 -- python

    # Check installed packages
    tox exec -e 3.13 -- pip list

    # Run a script with the environment's Python
    tox exec -e 3.13 -- python scripts/migrate.py --dry-run

The command must be in the environment's ``PATH`` or listed in :ref:`allowlist_externals`. ``tox exec`` is useful for
debugging, running one-off scripts, or interactively exploring an environment without modifying your configuration.

.. ------------------------------------------------------------------------------------------

.. Configuration (frequently needed)

.. ------------------------------------------------------------------------------------------

*********************************
 Override configuration defaults
*********************************

tox provides several ways to override configuration values without editing the configuration file.

**User-level configuration file**: tox reads a user-level config file whose location is shown in ``tox --help``. The
location can be changed via the ``TOX_CONFIG_FILE`` environment variable.

**Environment variables**: Any tox setting can be set via an environment variable with the ``TOX_`` prefix:

.. code-block:: bash

    # Use wheel packaging
    TOX_PACKAGE=wheel tox run -e 3.13

**CLI override**: The ``-x`` (or ``--override``) flag overrides any configuration value:

.. code-block:: bash

    # Force editable install for a specific environment
    tox run -e 3.13 -x "testenv:3.13.package=editable"

**********************************
 Use labels to group environments
**********************************

Labels let you assign tags to environments and run them as a group with ``tox run -m <label>``:

.. tab:: TOML

    .. code-block:: toml

         env_list = ["3.13", "3.12", "lint", "type"]

         [env_run_base]
         labels = ["test"]
         commands = [["pytest", "tests"]]

         [env.lint]
         labels = ["check"]
         skip_install = true
         deps = ["ruff"]
         commands = [["ruff", "check", "."]]

         [env.type]
         labels = ["check"]
         deps = ["mypy"]
         commands = [["mypy", "src"]]

.. tab:: INI

    .. code-block:: ini

         [tox]
         env_list = 3.13, 3.12, lint, type

         [testenv]
         labels = test
         commands = pytest tests

         [testenv:lint]
         labels = check
         skip_install = true
         deps = ruff
         commands = ruff check .

         [testenv:type]
         labels = check
         deps = mypy
         commands = mypy src

.. code-block:: bash

    # Run all environments labeled "check"
    tox run -m check

    # Run all environments labeled "test"
    tox run -m test

********************************
 Disallow unlisted environments
********************************

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

Running ``tox -e unt`` or ``tox -e unti`` would succeed without running any tests. An exception is made for environments
that look like Python version specifiers -- ``tox -e 3.13`` or ``tox -e py313`` would still work as intended.

.. _platform-specification:

**************************************
 Configure platform-specific settings
**************************************

Platform-dependent commands
===========================

The current platform (``sys.platform`` value like ``linux``, ``darwin``, ``win32``) is automatically available as an
implicit factor in all environments. Use platform factors to run different commands or set different dependencies per
platform without encoding the platform name in the environment:

.. tab:: INI

    .. code-block:: ini

         [tox]
         env_list = py313

         [testenv]
         deps =
             pytest
             linux,darwin: platformdirs>=3
             win32: platformdirs>=2
         commands =
             linux: python -c 'print("Running on Linux")'
             darwin: python -c 'print("Running on macOS")'
             win32: python -c 'print("Running on Windows")'
             python -m pytest

.. tab:: TOML

    .. code-block:: toml

         [env_list_base]
         env_list = ["py313"]

         [env_run_base]
         deps = [
             "pytest",
             { replace = "if", condition = "factor.linux or factor.darwin", then = ["platformdirs>=3"] },
             { replace = "if", condition = "factor.win32", then = ["platformdirs>=2"] },
         ]
         commands = [
             { replace = "if", condition = "factor.linux", then = [["python", "-c", "print('Running on Linux')"]] },
             { replace = "if", condition = "factor.darwin", then = [["python", "-c", "print('Running on macOS')"]] },
             { replace = "if", condition = "factor.win32", then = [["python", "-c", "print('Running on Windows')"]] },
             ["python", "-m", "pytest"],
         ]

This allows a single environment like ``py313`` to adapt its behavior based on the execution platform. The platform
factors work alongside regular factors from the environment name.

Common ``sys.platform`` values:

- ``linux`` - Linux systems
- ``darwin`` - macOS systems
- ``win32`` - Windows systems (both 32-bit and 64-bit)
- ``cygwin`` - Cygwin on Windows
- ``freebsd13`` - FreeBSD 13.x (version varies)
- ``openbsd7`` - OpenBSD 7.x (version varies)

Platform factors with environment factors
=========================================

Platform factors combine with regular environment factors. For example, an environment named ``py313-django50`` has
factors ``py313``, ``django50``, and the current platform:

.. tab:: INI

    .. code-block:: ini

        [tox]
        env_list = py3{12,13}-django{42,50}

        [testenv]
        deps =
            django42: Django>=4.2,<4.3
            django50: Django>=5.0,<5.1
            py312,linux: pytest-xdist  # only on Python 3.12 + Linux
            darwin: pyobjc-framework-Cocoa  # only on macOS
        commands =
            win32: python -c 'import winreg'  # only runs on Windows
            pytest

.. tab:: TOML

    .. code-block:: toml

        [env_list_base]
        env_list = ["py312-django42", "py312-django50", "py313-django42", "py313-django50"]

        [env_run_base]
        deps = [
            { replace = "if", condition = "factor.django42", then = ["Django>=4.2,<4.3"] },
            { replace = "if", condition = "factor.django50", then = ["Django>=5.0,<5.1"] },
            { replace = "if", condition = "factor.py312 and factor.linux", then = ["pytest-xdist"] },
            { replace = "if", condition = "factor.darwin", then = ["pyobjc-framework-Cocoa"] },
        ]
        commands = [
            { replace = "if", condition = "factor.win32", then = [["python", "-c", "import winreg"]] },
            ["pytest"],
        ]

Negation also works with platform factors:

.. tab:: INI

    .. code-block:: ini

        [testenv]
        deps =
            !win32: uvloop  # install uvloop on non-Windows platforms
            !darwin: pyinotify  # install pyinotify except on macOS

.. tab:: TOML

    .. code-block:: toml

        [env_run_base]
        deps = [
            { replace = "if", condition = "not factor.win32", then = ["uvloop"] },
            { replace = "if", condition = "not factor.darwin", then = ["pyinotify"] },
        ]

Platform skipping vs platform factors
=====================================

There are two ways to handle platform differences:

**Platform factors** (recommended) - Filter individual settings per platform:

.. tab:: INI

    .. code-block:: ini

        [testenv]
        commands =
            linux: pytest --numprocesses=auto
            darwin,win32: pytest

.. tab:: TOML

    .. code-block:: toml

        [env_run_base]
        commands = [
            { replace = "if", condition = "factor.linux", then = [["pytest", "--numprocesses=auto"]] },
            { replace = "if", condition = "factor.darwin or factor.win32", then = [["pytest"]] },
        ]

Settings without a platform factor apply to all platforms. This is ideal for most cross-platform projects.

**Platform skipping** - Skip entire environments when platform doesn't match:

.. tab:: INI

    .. code-block:: ini

        [testenv]
        platform = linux

.. tab:: TOML

    .. code-block:: toml

        [env_run_base]
        platform = "linux"

This skips the entire environment on non-Linux systems. Use this only when an environment genuinely cannot run on other
platforms (e.g., testing Linux-specific kernel features).

.. note::

    Platform factors are supported in both INI and TOML formats. INI uses inline syntax (``linux: command``), while TOML
    uses ``replace = "if"`` with ``factor.NAME`` conditions (see :ref:`conditional-value-reference`). Generative
    environments are currently only supported in the INI format (see :ref:`toml-feature-gaps`).

.. _howto_conditional_values:

*********************************
 Set values based on a condition
*********************************

.. versionadded:: 4.40 Conditional value replacement with ``env.VAR`` lookups.

.. versionchanged:: 4.42 Added ``factor.NAME`` lookups for environment name factors and platform.

TOML configurations can conditionally select values based on environment variables and factors using ``replace = "if"``.
The ``condition`` field accepts expressions with ``env.VAR`` lookups for environment variables, ``factor.NAME`` lookups
for environment name factors and platform, ``==``/``!=`` comparisons, and ``and``/``or``/``not`` boolean logic.

Set a variable depending on whether you are in CI:

.. code-block:: toml

    [env_run_base]
    set_env.MATURITY = { replace = "if", condition = "env.CI", then = "release", "else" = "dev" }

Add verbose flags to commands when a ``DEBUG`` variable is set:

.. code-block:: toml

    [env_run_base]
    commands = [["pytest", { replace = "if", condition = "env.DEBUG", then = ["-vv", "--tb=long"], "else" = [], extend = true }]]

Use different dependencies based on environment factors:

.. code-block:: toml

    [env_run_base]
    deps = [
        "pytest",
        { replace = "if", condition = "factor.django50", then = ["Django>=5.0,<5.1"], "else" = ["Django>=4.2,<4.3"] },
    ]

Combine multiple conditions (environment variables and factors):

.. code-block:: toml

    [env.deploy]
    commands = [["deploy", { replace = "if", condition = "env.CI and env.TAG_NAME != ''", then = ["--production"], "else" = ["--dry-run"], extend = true }]]

    [env_run_base]
    commands = [["pytest", { replace = "if", condition = "factor.linux and not env.CI", then = ["--numprocesses=auto"], "else" = [], extend = true }]]

For the full expression syntax and more examples, see :ref:`conditional-value-reference`.

*****************************************
 Handle env names that match subcommands
*****************************************

tox has built-in subcommands (``run``, ``list``, ``config``, etc.). If you have an environment name that matches a
subcommand, use the ``run`` subcommand explicitly:

.. code-block:: bash

    # This would be interpreted as "tox list", not "run the list environment"
    # tox -e list  # does NOT work as expected

    # Use the run subcommand explicitly
    tox run -e list

    # Or the short alias
    tox r -e list

.. ------------------------------------------------------------------------------------------

.. Dependencies & Packages

.. ------------------------------------------------------------------------------------------

.. _faq_custom_pypi_server:

.. _howto_custom_pypi_server:

**************************
 Use a custom PyPI server
**************************

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

***************************
 Use multiple PyPI servers
***************************

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

    Using an extra PyPI index for installing private packages may cause security issues. If ``package1`` is registered
    with the default PyPI index, pip will install ``package1`` from the default PyPI index, not from the extra one.

**********************
 Use constraint files
**********************

`Constraint files <https://pip.pypa.io/en/stable/user_guide/#constraints-files>`_ define version constraints for
dependencies without specifying what to install. When creating a test environment, tox invokes pip multiple times:

1. If :ref:`deps` is specified, it installs those dependencies first.
2. If the environment has a package (not :ref:`package` ``skip`` or :ref:`skip_install` ``true``), it:

   1. Installs the package dependencies.
   2. Installs the package itself.

When ``constrain_package_deps = true`` is set, ``{env_dir}/constraints.txt`` is generated during ``install_deps`` based
on the specifications in ``deps``. These constraints are then passed to pip during ``install_package_deps``, raising an
error when package dependencies conflict with test dependencies.

For stronger guarantees, set ``use_frozen_constraints = true`` to generate constraints from the exact installed versions
(via ``pip freeze``). This catches incompatibilities with any previously installed dependency.

.. note::

    Constraint files are a subset of requirement files. You can pass a constraint file wherever a requirement file is
    accepted.

************
 Use extras
************

If your package defines optional dependency groups (extras) in ``pyproject.toml``, you can install them in tox
environments via the :ref:`extras` configuration:

.. tab:: TOML

    .. code-block:: toml

         # pyproject.toml
         [project.optional-dependencies]
         testing = ["pytest>=8", "coverage"]
         docs = ["sphinx>=7"]

    .. code-block:: toml

         # tox.toml
         [env_run_base]
         extras = ["testing"]

         [env.docs]
         extras = ["docs"]
         commands = [["sphinx-build", "-W", "docs", "docs/_build/html"]]

.. tab:: INI

    .. code-block:: ini

         [testenv]
         extras = testing

         [testenv:docs]
         extras = docs
         commands = sphinx-build -W docs docs/_build/html

This installs your package together with the specified extras, avoiding the need to duplicate dependency lists in both
``pyproject.toml`` and your tox configuration.

************************************
 Install extras without the package
************************************

Sometimes you need the package's dependencies (including extras) without installing the package itself. For example,
coverage combining, documentation builds, or linting environments that share the same dependency set. Use ``package =
"deps-only"`` instead of ``skip_install = true`` combined with manually duplicated ``deps``:

.. tab:: TOML

    .. code-block:: toml

         # pyproject.toml
         [project]
         name = "myproject"
         dependencies = ["httpx>=0.27"]

         [project.optional-dependencies]
         docs = ["sphinx>=7", "furo"]

    .. code-block:: toml

         # tox.toml
         [env.docs]
         package = "deps-only"
         extras = ["docs"]
         commands = [["sphinx-build", "-W", "docs", "docs/_build/html"]]

.. tab:: INI

    .. code-block:: ini

         [testenv:docs]
         package = deps-only
         extras = docs
         commands = sphinx-build -W docs docs/_build/html

This reads your ``pyproject.toml`` directly (no build step) and installs ``httpx``, ``sphinx``, and ``furo`` into the
environment. If your dependencies are dynamic, tox falls back to using the packaging environment to extract metadata.

.. ------------------------------------------------------------------------------------------

.. Environment Customization

.. ------------------------------------------------------------------------------------------

*******************************
 Customize virtualenv creation
*******************************

tox uses :pypi:`virtualenv` to create Python virtual environments. Customize virtualenv behavior through environment
variables:

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

***************************
 Ignore command exit codes
***************************

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

**********************
 Retry flaky commands
**********************

Commands that fail due to transient errors (network timeouts, flaky tests) can be automatically retried using
:ref:`commands_retry`. The value specifies how many times to retry a failed command -- a value of ``2`` means each
command is attempted up to 3 times total. Retries apply to :ref:`commands_pre`, :ref:`commands`, and
:ref:`commands_post`. Commands prefixed with ``-`` (ignore exit code) are never retried.

.. tab:: TOML

    .. code-block:: toml

         [env.integration]
         description = "run integration tests with retries for flaky network calls"
         commands_retry = 2
         commands = [["pytest", "tests/integration"]]

.. tab:: INI

    .. code-block:: ini

         [testenv:integration]
         description = run integration tests with retries for flaky network calls
         commands_retry = 2
         commands = pytest tests/integration

**********************
 Control color output
**********************

tox uses colored output by default. To disable it, use any of these methods:

.. code-block:: bash

    # Via environment variable
    NO_COLOR=1 tox run

    # Via TERM
    TERM=dumb tox run

    # Via CLI flag
    tox run --colored no

.. ------------------------------------------------------------------------------------------

.. CI/CD & Automation

.. ------------------------------------------------------------------------------------------

.. _howto-ci:

****************************
 Use tox in CI/CD pipelines
****************************

tox works well in continuous integration systems. We recommend installing tox via `uv <https://docs.astral.sh/uv/>`__
for significantly faster setup times. Adding :pypi:`tox-uv` also replaces pip with uv inside tox environments, speeding
up dependency installation.

**GitHub Actions**:

.. code-block:: yaml

    # .github/workflows/tests.yml
    name: tests
    on: [push, pull_request]
    jobs:
      test:
        runs-on: ubuntu-latest
        strategy:
          matrix:
            python-version: ["3.12", "3.13", "3.14"]
        steps:
          - uses: actions/checkout@v4
          - uses: actions/setup-python@v5
            with:
              python-version: ${{ matrix.python-version }}
          - uses: astral-sh/setup-uv@v5
          - run: uv tool install tox --with tox-uv
          - run: tox run -e ${{ matrix.python-version }}

**GitLab CI**:

.. code-block:: yaml

    # .gitlab-ci.yml
    test:
      image: python:3.13
      before_script:
        - curl -LsSf https://astral.sh/uv/install.sh | sh
        - uv tool install tox --with tox-uv
      script:
        - tox run -e 3.13

.. ------------------------------------------------------------------------------------------

.. Documentation

.. ------------------------------------------------------------------------------------------

*********************************
 Build documentation with Sphinx
*********************************

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

*********************************
 Build documentation with mkdocs
*********************************

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

.. ------------------------------------------------------------------------------------------

.. Troubleshooting & Debugging

.. ------------------------------------------------------------------------------------------

*********************************
 Debug a failing tox environment
*********************************

When an environment fails, use these techniques to investigate:

1. **Increase verbosity** to see detailed command output:

   .. code-block:: bash

       tox run -e 3.13 -vv

2. **Inspect resolved configuration** to verify settings are what you expect:

   .. code-block:: bash

       # Show all configuration for an environment
       tox config -e 3.13

       # Show specific keys
       tox config -e 3.13 -k deps commands pass_env set_env

3. **Check log files** in ``.tox/<env_name>/log/`` for full command output with timestamps.
4. **Run a command interactively** inside the environment:

   .. code-block:: bash

       tox exec -e 3.13 -- python
       tox exec -e 3.13 -- pip list

5. **Force recreation** if you suspect a stale environment:

   .. code-block:: bash

       tox run -e 3.13 -r

.. _run-interactive-programs:

**************************
 Run interactive programs
**************************

Interactive programs like Python REPL, debuggers, or TUI applications need direct terminal access to handle user input
and query console properties. By default, tox pipes stdout/stderr to capture output for logging, which breaks terminal
APIs that require real console handles.

Use ``--no-capture`` (or ``-i``) to disable output capture and give the subprocess direct access to the terminal:

.. code-block:: bash

    # Open a Python REPL with full terminal support
    tox run -e 3.13 -i -- python

    # Run a debugger interactively
    tox run -e 3.13 -i -- python -m pdb script.py

    # Use a TUI application
    tox run -e 3.13 -i -- pytest --pdb

The ``--no-capture`` flag is mutually exclusive with ``--result-json`` (which requires output capture) and parallel mode
(where multiple environments' output would interleave). When enabled, tox cannot log command output to
``.tox/<env_name>/log/`` files.

.. note::

    ``tox exec`` always runs in interactive mode without output capture. Use ``tox exec`` for one-off commands that
    don't need the full environment setup (see :ref:`tox-exec`). Use ``tox run --no-capture`` when you need to run the
    configured commands interactively.

******************
 Access full logs
******************

tox logs command invocations inside ``.tox/<env_name>/log``. Each execution is recorded in a file named
``<index>-<run_name>.log``, containing the command, environment variables, working directory, exit code, and output.

Environment variables with names containing sensitive words (``access``, ``api``, ``auth``, ``client``, ``cred``,
``key``, ``passwd``, ``password``, ``private``, ``pwd``, ``secret``, ``token``) are logged with their values redacted to
prevent accidental secret leaking.

***************************************
 Understand InvocationError exit codes
***************************************

When a command executed by tox fails, an ``InvocationError`` is raised:

.. code-block:: shell

    ERROR: InvocationError for command
           '<command defined in tox config>' (exited with code 1)

Always check the documentation for the command that failed. For example, for :pypi:`pytest`, see the `pytest exit codes
<https://docs.pytest.org/en/latest/reference/exit-codes.html#exit-codes>`_.

On Unix systems, exit codes larger than 128 indicate a fatal signal. tox provides a hint in these cases:

.. code-block:: shell

    ERROR: InvocationError for command
           '<command>' (exited with code 139)
    Note: this might indicate a fatal error signal (139 - 128 = 11: SIGSEGV)

Signal numbers are documented in the `signal man page <https://man7.org/linux/man-pages/man7/signal.7.html>`_.

.. ------------------------------------------------------------------------------------------

.. Advanced & Specialized (niche topics at end)

.. ------------------------------------------------------------------------------------------

.. _eol-version-support:

**********************************
 Test end-of-life Python versions
**********************************

tox uses :pypi:`virtualenv` under the hood. Newer virtualenv versions drop support for older Python interpreters:

- `virtualenv 20.22.0 <https://virtualenv.pypa.io/en/latest/changelog.html#v20-22-0-2023-04-19>`_ dropped Python 3.6 and
  earlier
- `virtualenv 20.27.0 <https://virtualenv.pypa.io/en/latest/changelog.html#v20-27-0-2024-10-17>`_ dropped Python 3.7

To test against these versions, pin virtualenv:

.. tab:: TOML

    .. code-block:: toml

         requires = ["virtualenv<20.22.0"]

.. tab:: INI

    .. code-block:: ini

         [tox]
         requires = virtualenv<20.22.0

***************************************
 Use tox with different build backends
***************************************

tox works with any :PEP:`517`/:PEP:`518` compliant build backend. Configure the backend in ``pyproject.toml``:

**Hatchling** (``hatch``):

.. code-block:: toml

    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"

**Flit**:

.. code-block:: toml

    [build-system]
    requires = ["flit_core>=3.4"]
    build-backend = "flit_core.buildapi"

**PDM**:

.. code-block:: toml

    [build-system]
    requires = ["pdm-backend"]
    build-backend = "pdm.backend"

tox automatically detects and uses whatever backend is specified in ``[build-system]``. No additional tox configuration
is needed. For build backends that need extra configuration during the build, use :ref:`config_settings_build_wheel` and
related options.

**********************************
 Migrate from tox.ini to tox.toml
**********************************

TOML is the recommended configuration format for new projects. Here is how common INI patterns translate to TOML:

**Basic structure**:

.. tab:: TOML

    .. code-block:: toml

         # tox.toml - values at root level are core settings
         requires = ["tox>=4.20"]
         env_list = ["3.13", "3.12", "lint"]

         # base settings for run environments
         [env_run_base]
         deps = ["pytest>=8"]
         commands = [["pytest", "tests"]]

         # environment-specific overrides
         [env.lint]
         skip_install = true
         deps = ["ruff"]
         commands = [["ruff", "check", "."]]

.. tab:: INI

    .. code-block:: ini

         [tox]
         requires = tox>=4.20
         env_list = 3.13, 3.12, lint

         [testenv]
         deps = pytest>=8
         commands = pytest tests

         [testenv:lint]
         skip_install = true
         deps = ruff
         commands = ruff check .

**Key differences**:

- Strings must be quoted in TOML: ``description = "run tests"`` vs ``description = run tests``
- Lists use JSON syntax: ``deps = ["pytest", "ruff"]`` vs multi-line ``deps = \n pytest \n ruff``
- Commands are list-of-lists: ``commands = [["pytest", "tests"]]`` vs ``commands = pytest tests``
- Positional arguments use replacement objects: ``{ replace = "posargs", default = ["tests"] }`` vs ``{posargs:tests}``
- Environment variables in ``set_env`` use ``{ replace = "env", name = "VAR" }`` vs ``{env:VAR}``
- Section references use ``{ replace = "ref", ... }`` vs ``{[section]key}``
- Factor conditions use ``{ replace = "if", condition = "factor.NAME", ... }`` vs ``NAME:`` (see
  :ref:`toml-feature-gaps`)
- No generative environment lists in TOML (see :ref:`toml-feature-gaps`)

*************************************
 Format your tox configuration files
*************************************

Consistent formatting makes configuration files easier to read and review. The tox-dev organization maintains
opinionated formatters for both TOML and INI configurations, available as pre-commit hooks or standalone CLI tools.

.. tab:: TOML

    Use :pypi:`tox-toml-fmt` for ``tox.toml`` or TOML-based configuration in ``pyproject.toml``. It standardizes
    quoting, array formatting, and table organization:

    .. code-block:: yaml

        # .pre-commit-config.yaml
        - repo: https://github.com/tox-dev/toml-fmt
          rev: "1.6.0"
          hooks:
            - id: tox-toml-fmt

    Also available as a standalone command via ``pipx install tox-toml-fmt``.

.. tab:: INI

    Use :pypi:`tox-ini-fmt` for ``tox.ini`` files. It normalizes boolean fields, orders sections consistently, and
    formats multi-line values with uniform indentation:

    .. code-block:: yaml

        # .pre-commit-config.yaml
        - repo: https://github.com/tox-dev/tox-ini-fmt
          rev: "1.7.1"
          hooks:
            - id: tox-ini-fmt

    Also available as a standalone command via ``pipx install tox-ini-fmt``.
