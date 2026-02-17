##########
 Concepts
##########

**********
 Overview
**********

tox is an environment orchestrator. Use it to define how to set up and execute various tools on your projects. The tool
can set up environments for and invoke:

- test runners (such as :pypi:`pytest`),
- linters (e.g., :pypi:`ruff`),
- formatters (for example :pypi:`black` or :pypi:`isort`),
- documentation generators (e.g., :pypi:`Sphinx`),
- build and publishing tools (e.g., :pypi:`build` with :pypi:`twine`),
- ...

For a step-by-step introduction, see the :doc:`tutorial/getting-started` tutorial. For practical recipes, see
:doc:`how-to/usage`.

*****************
 System overview
*****************

Below is a graphical representation of the tox lifecycle:

.. mermaid::

    flowchart TD
        start(( )) --> config[Load configuration]

        config --> envloop

        subgraph envloop [for each selected environment]
            direction TB
            create[Create environment]
            create --> deps[Install dependencies]
            deps --> pkg{package project?}
            pkg -- yes --> build[Build and install package]
            pkg -- no --> extra
            build --> extra[Run extra_setup_commands]
            extra --> cmds
            cmds[Run commands]
        end

        cmds --> report[Report results]
        report --> done(( ))

        classDef configStyle fill:#dbeafe,stroke:#3b82f6,stroke-width:2px,color:#1e3a5f
        classDef envStyle fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#14532d
        classDef pkgStyle fill:#ffedd5,stroke:#f97316,stroke-width:2px,color:#7c2d12
        classDef setupStyle fill:#fde68a,stroke:#fbbf24,stroke-width:2px,color:#78350f
        classDef cmdStyle fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px,color:#3b0764
        classDef reportStyle fill:#ccfbf1,stroke:#14b8a6,stroke-width:2px,color:#134e4a
        classDef decisionStyle fill:#fef9c3,stroke:#eab308,stroke-width:2px,color:#713f12

        class config configStyle
        class create,deps envStyle
        class build pkgStyle
        class extra setupStyle
        class cmds cmdStyle
        class report reportStyle
        class pkg decisionStyle

The primary tox states are:

1. **Configuration:** load tox configuration files (such as ``tox.toml``, ``tox.ini``, ``pyproject.toml`` and
   ``toxfile.py``) and merge it with options from the command line plus the operating system environment variables.
   Configuration is loaded lazily -- individual environment settings are only read when that environment is used.
2. **Environment**: for each selected tox environment (e.g. ``3.13``, ``lint``) do:

   1. **Creation**: create a fresh environment; by default :pypi:`virtualenv` is used, but configurable via
      :ref:`runner`. For ``virtualenv`` tox will use the `virtualenv discovery logic
      <https://virtualenv.pypa.io/en/latest/user_guide.html#python-discovery>`_ where the python specification is
      defined by the tox environments :ref:`base_python` (if not set will default to the environments name). This is
      created at first run only to be reused at subsequent runs. If certain aspects of the project change (python
      version, dependencies removed, etc.), a re-creation of the environment is automatically triggered. To force the
      recreation tox can be invoked with the :ref:`recreate` flag (``-r``).
   2. **Install dependencies** (optional): install the environment dependencies specified inside the ``deps``
      configuration section, and then the earlier packaged source distribution. By default ``pip`` is used to install
      packages, however one can customize this via ``install_command``.
   3. **Packaging** (optional): create a distribution of the current project (see :ref:`packaging` below).
   4. **Extra setup commands** (optional): run the :ref:`extra_setup_commands` specified. These execute after all
      installations complete but before test commands, and run during the ``--notest`` phase.
   5. **Commands**: run the specified commands in the specified order. Whenever the exit code of any of them is not
      zero, stop and mark the environment failed. When you start a command with a dash character, the exit code will be
      ignored.

3. **Report** print out a report of outcomes for each tox environment:

   .. code-block:: bash

       ____________________ summary ____________________
       3.13: commands succeeded
       ERROR:   3.12: commands failed

   Only if all environments ran successfully tox will return exit code ``0`` (success). In this case you'll also see the
   message ``congratulations :)``.

Environment variable handling
=============================

tox takes care of environment variable isolation. By default, it removes system environment variables not specified via
:ref:`pass_env` and alters the ``PATH`` variable so that commands resolve within the current active tox environment.
External commands need to be explicitly allowed via :ref:`allowlist_externals`.

**Evaluation order**: tox composes the environment for command execution in this order:

1. **pass_env** -- glob patterns are matched against the host ``os.environ``. Matching variables are passed through.
2. **disallow_pass_env** -- exclusion patterns are applied to remove specific variables after ``pass_env`` expansion.
3. **PATH** -- tox prepends the virtual environment's binary directory to ``PATH``, so commands resolve inside the
   virtualenv first.
4. **set_env** -- values defined here are applied last and can override anything from the previous steps, including
   ``PATH``.
5. **Injected variables** -- tox adds ``TOX_ENV_NAME``, ``TOX_WORK_DIR``, ``TOX_ENV_DIR``, ``VIRTUAL_ENV``,
   ``PIP_USER=0``, and ``PYTHONIOENCODING=utf-8``. These cannot be overridden.

**PATH behavior**: because tox prepends the virtualenv ``bin/`` directory to ``PATH`` at step 3, commands like
``python`` and ``pip`` resolve to the virtualenv versions. If you override ``PATH`` in ``set_env``, be aware that this
replaces the composed ``PATH`` entirely -- you should include ``{env_bin_dir}`` in your custom value to preserve
virtualenv resolution:

.. tab:: TOML

    .. code-block:: toml

       [env_run_base]
       set_env.PATH = "{env_bin_dir}{:}/usr/local/bin{:}{env:PATH}"

.. tab:: INI

    .. code-block:: ini

       [testenv]
       set_env =
           PATH = {env_bin_dir}{:}/usr/local/bin{:}{env:PATH}

**Conditional environment variables**: in INI, ``set_env`` supports PEP 508-style markers separated by ``;`` to
conditionally set variables based on platform:

.. code-block:: ini

    [testenv]
    set_env =
        COVERAGE_FILE = {work_dir}/.coverage.{env_name}
        LDFLAGS = -L/usr/local/lib ; sys_platform == "darwin"

Dependency change detection
===========================

tox discovers package dependency changes (via :PEP:`621` or :PEP:`517`
``prepare_metadata_for_build_wheel``/``build_wheel`` metadata). When new dependencies are added they are installed on
the next run. When a dependency is removed the entire environment is automatically recreated. This also works for
``requirements`` files within :ref:`deps`. In most cases you should never need to use the ``--recreate`` flag -- tox
detects changes and applies them automatically.

***************
 Main features
***************

- **automation of tedious Python related test activities**
- **test your Python package against many interpreter and dependency configurations**

  - automatic customizable (re)creation of :pypi:`virtualenv` test environments
  - installs your project into each virtual environment
  - test-tool agnostic: runs pytest, unittest, or any other test runner

- **plugin system** to modify tox execution with simple hooks
- uses :pypi:`pip` and :pypi:`virtualenv` by default; plugins can replace either
- **cross-Python compatible**: tox requires CPython 3.10 and higher, but it can create environments for older versions.
  Special configuration might be required: :ref:`eol-version-support`.
- **cross-platform**: Windows, macOS and Unix style environments
- **full interoperability with devpi**: is integrated with and is used for testing in the :pypi:`devpi` system, a
  versatile PyPI index server and release managing tool
- **concise reporting** about tool invocations and configuration errors
- supports using different / multiple PyPI index servers

.. _packaging:

***********
 Packaging
***********

tox builds projects in a :PEP:`518` compatible virtual environment and communicates with the build backend according to
the interface defined in :PEP:`517` and :PEP:`660`. To define package build dependencies and specify the build backend
to use, create a ``pyproject.toml`` at the root of the project. For example to use hatch:

.. code-block:: toml

    [build-system]
    build-backend = "hatchling.build"
    requires = ["hatchling>=0.22", "hatch-vcs>=0.2"]

Package modes
=============

The :ref:`package` configuration controls how the project is packaged:

.. mermaid::

    flowchart TD
        pkg{package setting}
        pkg -- sdist --> sdist[sdist — default]
        pkg -- wheel --> wheel[wheel — faster install]
        pkg -- editable --> editable[editable — PEP 660]
        pkg -- editable-legacy --> legacy[editable-legacy — pip -e]
        pkg -- skip --> skip[skip — no packaging]
        pkg -- external --> external[external — provided]

        sdist --> env_pkg[build env: .pkg]
        wheel --> env_wheel[build env: .pkg-cpython313]
        editable --> env_wheel
        legacy --> env_pkg
        skip --> no_env[no build env]
        external --> no_env

        classDef decisionStyle fill:#fef9c3,stroke:#eab308,stroke-width:2px,color:#713f12
        classDef pkgStyle fill:#ffedd5,stroke:#f97316,stroke-width:2px,color:#7c2d12
        classDef envStyle fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#14532d
        classDef skipStyle fill:#f3f4f6,stroke:#9ca3af,stroke-width:2px,color:#374151

        class pkg decisionStyle
        class sdist,wheel,editable,legacy,external pkgStyle
        class env_pkg,env_wheel envStyle
        class skip,no_env skipStyle

- ``sdist`` (default): builds a source distribution
- ``wheel``: builds a wheel (much faster to install)
- ``editable``: builds an editable wheel as defined by :PEP:`660`
- ``editable-legacy``: invokes pip with ``-e`` (fallback when the backend doesn't support PEP 660)
- ``skip``: skips packaging entirely (useful for tools like linters that don't need the project installed)
- ``external``: uses an externally provided package

Build environments
==================

tox uses a virtual environment for building, whose name depends on the artifact type:

- For source distributions: the :ref:`package_env` (default ``.pkg``)
- For wheels: the :ref:`wheel_build_env` (default ``.pkg-<impl><version>``, e.g. ``.pkg-cpython313``)

For pure Python projects (no C extensions), set :ref:`wheel_build_env` to the same value as :ref:`package_env`. This way
the wheel is built once and reused for all tox environments:

.. tab:: TOML

    .. code-block:: toml

         [env_run_base]
         package = "wheel"
         wheel_build_env = ".pkg"

.. tab:: INI

    .. code-block:: ini

         [testenv]
         package = wheel
         wheel_build_env = .pkg

Packaging environment configuration
===================================

Packaging environments do **not** inherit settings from ``env_run_base`` (TOML) or ``[testenv]`` (INI). Instead, they
inherit from the ``env_pkg_base`` table (TOML) or ``[pkgenv]`` section (INI). This prevents test settings from
conflicting with packaging settings.

.. tab:: TOML

    .. code-block:: toml

       [env_pkg_base]
       pass_env = ["PKG_CONFIG", "PKG_CONFIG_PATH"]

.. tab:: INI

    .. code-block:: ini

       [pkgenv]
       pass_env =
           PKG_CONFIG
           PKG_CONFIG_PATH

To configure a specific packaging environment, use the standard environment syntax (e.g. ``[testenv:.pkg]`` in INI or
``env.".pkg"`` in TOML).

.. _auto-provisioning:

*******************
 Auto-provisioning
*******************

When the installed tox version does not satisfy either the :ref:`requires` or the :ref:`min_version`, tox automatically
creates a virtual environment under :ref:`provision_tox_env` name that satisfies those constraints and delegates all
calls to this meta environment.

.. mermaid::

    flowchart TD
        invoke[tox invoked] --> check{requires and min_version satisfied?}
        check -- yes --> run[run normally]
        check -- no --> create[create .tox/.tox virtualenv]
        create --> install[install tox + required plugins]
        install --> delegate[re-invoke tox inside .tox/.tox]
        delegate --> run

        classDef decisionStyle fill:#fef9c3,stroke:#eab308,stroke-width:2px,color:#713f12
        classDef envStyle fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#14532d
        classDef cmdStyle fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px,color:#3b0764

        class check decisionStyle
        class create,install envStyle
        class invoke,run,delegate cmdStyle

For example given:

.. tab:: TOML

    .. code-block:: toml

         requires = ["tox>=4", "tox-uv>=1"]

.. tab:: INI

    .. code-block:: ini

         [tox]
         requires =
             tox>=4
             tox-uv>=1

tox will automatically ensure that both the minimum version and requires constraints are satisfied, by creating a
virtual environment under ``.tox``, and then installing into it ``tox>=4`` and ``tox-uv>=1``. Afterwards all tox
invocations are forwarded to the tox installed inside ``.tox/.tox`` (referred to as the provisioned tox).

This allows tox to automatically set up itself with all its plugins for the current project. If the host tox satisfies
the constraints no provisioning is done (to avoid setup cost and indirection).

.. note::

    The provisioning environment (``.tox`` by default) does **not** inherit settings from ``env_run_base`` (TOML) or
    ``[testenv]`` (INI). It must be explicitly configured if you need to customize it (e.g. ``env.".tox"`` in TOML or
    ``[testenv:.tox]`` in INI).

.. _parallel_mode:

***************
 Parallel mode
***************

tox allows running environments in parallel mode via the ``parallel`` sub-command:

- After the packaging phase completes tox runs environments in parallel processes (multi-thread based).
- The ``--parallel`` flag takes an argument specifying the degree of parallelization, defaulting to ``auto``:

  - ``all`` to run all invoked environments in parallel,
  - ``auto`` to limit it to CPU count,
  - or pass an integer to set that limit.

- Parallel mode displays a progress spinner while running environments in parallel, and reports outcome as soon as
  environments complete. To run without the spinner, use ``--parallel-no-spinner``.
- Parallel mode by default shows output only of failed environments and ones marked as :ref:`parallel_show_output` ``=
  true``.
- Environments can declare dependencies on other environments via :ref:`depends`. tox re-orders the environment list to
  satisfy these dependencies (also for sequential runs). In parallel mode, tox only schedules an environment once all of
  its dependencies have finished (independent of their outcome).

  ``depends`` supports glob patterns (``*``, ``?``, ``[seq]``) using :py:mod:`fnmatch`, so instead of listing each
  environment explicitly you can write ``depends = 3.*`` to match all environments starting with ``3.``.

  .. warning::

      ``depends`` does not pull in dependencies into the run target. For example, if you select ``3.13,3.12,coverage``
      via ``-e`` tox will only run those three (even if ``coverage`` may specify as ``depends`` other targets too --
      such as ``3.13, 3.12, 3.11``).

- ``--parallel-live`` / ``-o`` shows live output of stdout and stderr, and turns off the spinner.
- Parallel evaluation disables standard input. Use non-parallel invocation if you need standard input.

Example final output:

.. code-block:: bash

    $ tox -e 3.13,3.12,coverage -p all
    ✔ OK 3.12 in 9.533 seconds
    ✔ OK 3.13 in 9.96 seconds
    ✔ OK coverage in 2.0 seconds
    ___________________________ summary ______________________________________________________
      3.13: commands succeeded
      3.12: commands succeeded
      coverage: commands succeeded
      congratulations :)

Example progress bar, showing a rotating spinner, the number of environments running and their list (limited up to 120
characters):

.. code-block:: bash

    ⠹ [2] 3.13 | 3.12

****************
 Fail-fast mode
****************

When running multiple environments, tox normally runs all of them even if an early environment fails. The
``--fail-fast`` flag stops execution after the first environment failure, saving time in CI pipelines and development
workflows.

.. code-block:: bash

    tox run -e 3.13,3.12,3.11 --fail-fast

You can also enable it per-environment via the ``fail_fast`` configuration:

.. tab:: TOML

    .. code-block:: toml

       [env.critical]
       fail_fast = true
       commands = [["pytest", "tests/critical"]]

.. tab:: INI

    .. code-block:: ini

       [testenv:critical]
       fail_fast = true
       commands = pytest tests/critical

The fail-fast behavior:

- Works in both sequential and parallel execution modes.
- In parallel mode, environments already running when a failure occurs will continue to completion. Only environments
  not yet queued will be skipped.
- Respects :ref:`ignore_outcome` -- environments with ``ignore_outcome = true`` will not trigger fail-fast even if they
  fail.
- Respects environment dependencies defined via :ref:`depends` -- dependent environments will not run if a dependency
  fails with fail-fast enabled.
- Environments not yet started are skipped with exit code -2 and marked as ``SKIP`` in the output.
- The overall tox exit code will be the exit code of the first failed environment.

***************************
 Configuration inheritance
***************************

Every tox environment has its own configuration section. If a value is not defined in the environment-specific section,
it falls back to the base section (:ref:`base` configuration). For ``tox.toml`` this is the ``env_run_base`` table, for
``tox.ini`` this is ``[testenv]``. If the base section also lacks the value, the configuration default is used.

.. tab:: TOML

    .. code-block:: toml

         [env_run_base]
         commands = [["pytest", "tests"]]

         [env.test]
         description = "run the test suite with pytest"

.. tab:: INI

    .. code-block:: ini

         [testenv]
         commands = pytest tests

         [testenv:test]
         description = run the test suite with pytest

Here ``test`` inherits ``commands`` from the base because it is not specified in ``[env.test]``.

******************
 Related projects
******************

tox has influenced several other projects in the Python test automation space. If tox doesn't quite fit your needs or
you want to do more research, we recommend taking a look at these projects:

- `nox <https://nox.thea.codes/en/stable/>`__ is a project similar in spirit to tox but different in approach. The
  primary key difference is that it uses Python scripts instead of a configuration file. It might be useful if you find
  tox configuration too limiting but aren't looking to move to something as general-purpose as ``Invoke`` or ``make``.
- `Invoke <https://www.pyinvoke.org/>`__ is a general-purpose task execution library, similar to Make. Invoke is far
  more general-purpose than tox but it does not contain the Python testing-specific features that tox specializes in.
