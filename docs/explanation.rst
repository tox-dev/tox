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
            create --> depmode{pylock set?}
            depmode -- yes --> pylock[Install from pylock.toml]
            depmode -- no --> deps[Install deps + dependency groups]
            pylock --> pkg{package project?}
            deps --> pkg
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
        classDef pylockStyle fill:#e0e7ff,stroke:#6366f1,stroke-width:2px,color:#312e81

        class config configStyle
        class create,deps envStyle
        class build pkgStyle
        class extra setupStyle
        class cmds cmdStyle
        class report reportStyle
        class depmode,pkg decisionStyle
        class pylock pylockStyle

The primary tox states are:

1. **Configuration:** load tox configuration files (such as ``tox.toml``, ``tox.ini``, ``pyproject.toml`` and
   ``toxfile.py``) and merge it with options from the command line plus the operating system environment variables.
   Configuration is loaded lazily -- individual environment settings are only read when that environment is used.
2. **Environment**: for each selected tox environment (e.g. ``3.13``, ``lint``) do:

   1. **Creation**: create a fresh environment; by default :pypi:`virtualenv` is used, but configurable via
      :ref:`runner`. For ``virtualenv`` tox will use the `virtualenv discovery logic
      <https://virtualenv.pypa.io/en/latest/user_guide.html#python-discovery>`_ where the python specification is
      defined by the tox environments :ref:`base_python` (if not set will try to extract it from the environment name,
      then fall back to :ref:`default_base_python`, and finally to the Python running tox). This is created at first run
      only to be reused at subsequent runs. If certain aspects of the project change (python version, dependencies
      removed, etc.), a re-creation of the environment is automatically triggered. To force the recreation tox can be
      invoked with the :ref:`recreate` flag (``-r``). When recreation occurs, any :ref:`recreate_commands` run inside
      the old environment before its directory is removed -- this lets tools like pre-commit clean their external
      caches. Failures in these commands are logged as warnings but never block the recreation.
   2. **Install dependencies** (optional): install the environment dependencies. When :ref:`pylock` is set, tox installs
      locked dependencies from the :PEP:`751` lock file (filtered by extras, dependency groups, and platform markers).
      Otherwise, it installs :ref:`deps` and :ref:`dependency_groups`. By default ``pip`` is used to install packages,
      however one can customize this via ``install_command``.
   3. **Packaging** (optional): create a distribution of the current project (see :ref:`packaging` below).

   Steps 2 and 3 can be selectively skipped with CLI flags:

   - ``--skip-pkg-install`` skips step 3 only (packaging and package installation), while still installing dependencies.
   - ``--skip-env-install`` skips both steps 2 and 3 entirely, reusing the environment as-is. This is useful when
     working offline or when the environment is already fully set up from a previous run. See :ref:`skip-env-install`
     for practical usage.

   4. **Extra setup commands** (optional): run the :ref:`extra_setup_commands` specified. These execute after all
      installations complete but before test commands, and run during the ``--notest`` phase.
   5. **Commands**: run the specified commands in the specified order. Whenever the exit code of any of them is not
      zero, stop and mark the environment failed. When you start a command with a dash character, the exit code will be
      ignored. If :ref:`commands_retry` is set, failed commands are retried up to the configured number of times before
      being treated as a failure.

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

.. _conditional-values-explained:

Conditional value evaluation
============================

.. versionadded:: 4.40

TOML configurations support ``replace = "if"`` to conditionally select values at configuration load time. The
``condition`` field accepts expressions that are parsed using Python's ``ast`` module and evaluated against the host
``os.environ``.

The expression language supports:

- ``env.VAR`` -- resolves to the value of the environment variable ``VAR``, or empty string if unset. An empty string is
  falsy, any non-empty string is truthy.
- ``'literal'`` -- a string literal for comparison.
- ``==``, ``!=`` -- string equality and inequality.
- ``and``, ``or``, ``not`` -- boolean combinators with standard Python precedence.

Conditions are evaluated before ``set_env`` is applied. The ``env.VAR`` lookup reads directly from ``os.environ``, not
from the tox ``set_env`` configuration. This avoids circular dependencies -- a ``set_env`` value can use ``replace =
"if"`` to check a host variable without triggering a recursive load.

Both ``then`` and ``else`` values are processed through the normal TOML replacement pipeline, so they can contain nested
substitutions like ``{env_name}`` or ``{ replace = "env", ... }``. Only the selected branch is evaluated.

For syntax details and examples, see :ref:`conditional-value-reference`. For practical recipes, see
:ref:`howto_conditional_values`.

Dependency change detection
===========================

tox discovers package dependency changes (via :PEP:`621` or :PEP:`517`
``prepare_metadata_for_build_wheel``/``build_wheel`` metadata). When new dependencies are added they are installed on
the next run. When a dependency is removed the entire environment is automatically recreated. This also works for
``requirements`` files within :ref:`deps`. In most cases you should never need to use the ``--recreate`` flag -- tox
detects changes and applies them automatically.

.. _pylock-explanation:

Lock file installation (PEP 751)
================================

.. versionadded:: 4.44

The :ref:`pylock` setting installs dependencies from a :PEP:`751` lock file (``pylock.toml``). It is mutually exclusive
with :ref:`deps` — a lock file already contains all transitive dependencies with exact versions, so mixing both sources
would create conflicts. Lock files differ from ``deps`` in that every dependency is already resolved — the file contains
exact versions, markers, and artifact URLs for every package.

**Extras and dependency groups:** lock files can declare ``extras`` and ``dependency-groups`` at the top level, with
per-package markers like ``'docs' in extras`` or ``'dev' in dependency_groups``. Use the existing :ref:`extras` and
:ref:`dependency_groups` settings to select which groups to include — tox evaluates these markers together with platform
markers (``sys_platform``, ``python_version``, etc.) against the **target** Python interpreter (not the host running
tox) to filter packages at install time.

**How it works today:** pip does not yet support installing from ``pylock.toml`` directly. tox parses the lock file
using the ``packaging.pylock`` module, evaluates markers to filter packages, transpiles matching packages to a temporary
requirements file (``{env_dir}/pylock.txt``), and passes it to pip with ``--no-deps``. The ``--no-deps`` flag prevents
pip from re-resolving transitive dependencies, ensuring the exact versions from the lock file are installed.

**Plugin support:** the ``Pylock`` object is passed through the ``tox_on_install`` plugin hook. Installer plugins can
inspect it via ``isinstance(arguments, Pylock)`` and handle lock files natively (e.g. ``uv pip install --pylock``)
instead of relying on the transpile path.

**Future:** when pip gains native ``pylock.toml`` support, the transpile step will be replaced with a direct pip
invocation. No configuration changes will be needed.

**Change detection** works the same as for ``deps``: tox caches the resolved requirements. When packages are added, only
the new ones are installed. When packages are removed, the environment is recreated.

Open-ended range bounds
=======================

Both INI and TOML support generative environment lists with open-ended ranges. INI uses curly-brace syntax
(``py3{10-}``), while TOML uses range dicts (``{ prefix = "py3", start = 10 }``). Instead of probing the system for
available interpreters (which would be slow and environment-dependent), tox tracks the `supported CPython versions
<https://devguide.python.org/versions/>`_ via two constants:

- ``LATEST_PYTHON_MINOR_MIN`` -- the oldest supported CPython minor version (currently **10**, for Python 3.10)
- ``LATEST_PYTHON_MINOR_MAX`` -- the latest supported CPython minor version (currently **14**, for Python 3.14)

These values are updated with each tox release. A right-open range ``{10-}`` uses ``LATEST_PYTHON_MINOR_MAX`` as its
upper bound; a left-open range ``{-13}`` uses ``LATEST_PYTHON_MINOR_MIN`` as its lower bound.

This design is deterministic and fast -- the expansion happens at configuration load time with no I/O -- while keeping
environment lists future-proof across tox upgrades. Environments for interpreters not installed on the system are
naturally skipped by the :ref:`skip_missing_interpreters` setting.

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
        pkg -- sdist-wheel --> sdistwheel[sdist-wheel — build wheel from sdist]
        pkg -- editable --> editable[editable — PEP 660]
        pkg -- editable-legacy --> legacy[editable-legacy — pip -e]
        pkg -- skip --> skip[skip — no packaging]
        pkg -- external --> external[external — provided]

        sdist --> env_pkg[build env: .pkg]
        wheel --> env_wheel[build env: .pkg-cpython313]
        sdistwheel --> env_pkg[sdist in: .pkg]
        sdistwheel --> env_wheel2[wheel in: .pkg-cpython313]
        editable --> env_wheel
        legacy --> env_pkg
        skip --> no_env[no build env]
        external --> no_env

        classDef decisionStyle fill:#fef9c3,stroke:#eab308,stroke-width:2px,color:#713f12
        classDef pkgStyle fill:#ffedd5,stroke:#f97316,stroke-width:2px,color:#7c2d12
        classDef envStyle fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#14532d
        classDef skipStyle fill:#f3f4f6,stroke:#9ca3af,stroke-width:2px,color:#374151

        class pkg decisionStyle
        class sdist,wheel,sdistwheel,editable,legacy,external pkgStyle
        class env_pkg,env_wheel,env_wheel2 envStyle
        class skip,no_env skipStyle

- ``sdist`` (default): builds a source distribution
- ``wheel``: builds a wheel (much faster to install)
- ``sdist-wheel``: builds a source distribution first, then builds a wheel from that sdist (validates sdist
  completeness)
- ``editable``: builds an editable wheel as defined by :PEP:`660`
- ``editable-legacy``: invokes pip with ``-e`` (fallback when the backend doesn't support PEP 660)
- ``skip``: skips packaging entirely (useful for tools like linters that don't need the project installed)
- ``external``: uses an externally provided package

Build environments
==================

tox uses a virtual environment for building, whose name depends on the artifact type:

- For source distributions: the :ref:`package_env` (default ``.pkg``)
- For wheels: the :ref:`wheel_build_env` (default ``.pkg-<impl><version>``, e.g. ``.pkg-cpython313``)
- For sdist-wheel: uses two environments — the :ref:`package_env` for building the sdist, and the :ref:`wheel_build_env`
  (default ``.pkg-<impl><version>``) for building the wheel from the extracted sdist

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

.. _virtualenv-version-pinning:

****************************
 Virtualenv version pinning
****************************

tox creates isolated environments using :pypi:`virtualenv`, which it imports as a library. This works well when the
installed virtualenv supports all target Python versions, but breaks down at the edges: older virtualenv releases
(pre-20.22) are required for Python 3.6 support, while the latest virtualenv is needed for Python 3.15+. Since tox can
only import one virtualenv version per process, projects that need both old and new Pythons in a single ``tox.toml`` hit
a wall.

The :ref:`virtualenv_spec` setting resolves this by decoupling the virtualenv used for environment creation from the one
tox imports. When set, tox:

1. Creates a bootstrap venv (using the stdlib ``venv`` module) in ``.tox/.virtualenv-bootstrap/``.
2. Installs the specified virtualenv version into that bootstrap venv via pip.
3. Runs the bootstrapped virtualenv as a subprocess instead of calling ``session_via_cli()`` from the imported library.

The bootstrap is content-addressed by a hash of the spec string, so different specs get separate cached environments. A
file lock protects against concurrent bootstrap creation (relevant in parallel mode). Once bootstrapped, subsequent runs
skip directly to step 3.

When ``virtualenv_spec`` is empty (the default), tox uses the imported virtualenv with zero overhead -- the subprocess
path only activates when explicitly configured. The spec is included in the environment cache key, so changing it
triggers automatic recreation.

This design mirrors tox's own auto-provisioning mechanism (``requires`` / ``min_version``), where tox bootstraps itself
into a separate environment when the running installation doesn't meet the declared requirements.

*******************
 Known limitations
*******************

Interactive terminal programs
=============================

Programs that require advanced terminal control — such as IPython, debuggers with rich UIs, or any tool built on
`prompt_toolkit <https://python-prompt-toolkit.readthedocs.io/>`__ — need direct terminal access to work correctly.

By default, tox captures subprocess output by routing ``stdout`` and ``stderr`` through pseudo-terminal (PTY) pairs.
This is necessary for logging, result reporting, and colorized output. However, the subprocess's ``stdin`` remains
connected to the real terminal. This means ``stdin`` and ``stdout`` are on *different* terminal devices.

Libraries like ``prompt_toolkit`` assume all streams share the same terminal. They set raw mode on ``stdin`` (to read
individual keystrokes) while writing VT100 escape sequences to ``stdout`` (for cursor positioning, screen clearing,
etc.). When ``stdout`` goes through tox's capture buffer instead of directly to the terminal, escape sequences are
delayed and the synchronous terminal control these libraries depend on breaks.

Solution:

Use the ``--no-capture`` (or ``-i``) flag to disable output capture and give the subprocess direct terminal access:

.. code-block:: bash

    # Run IPython with full terminal support
    tox run -e 3.13 -i -- ipython

    # Run debugger interactively
    tox run -e 3.13 -i -- python -m pdb script.py

This flag is mutually exclusive with ``--result-json`` and parallel mode. See :ref:`run-interactive-programs` for
details.

Alternative workarounds if you cannot use ``--no-capture``:

- For IPython, pass ``--simple-prompt`` to disable ``prompt_toolkit``'s advanced terminal features.
- For other tools, look for a "dumb terminal" or "no-color" mode that avoids VT100 escape sequences.

Debian/Ubuntu without ``python3-venv``
======================================

On Debian and Ubuntu, the system Python is split into multiple packages. The ``python3`` package does not include the
:mod:`venv` module or :mod:`ensurepip` — these are in the separate ``python3-venv`` package.

tox itself is **not affected** because it uses :pypi:`virtualenv` (which bundles its own bootstrap mechanism) rather
than stdlib :mod:`venv`. However, tools that tox *runs as commands* inside environments may use stdlib :mod:`venv`
internally and fail. A common example is :pypi:`build` (``pyproject-build``), which creates an isolated build
environment using :mod:`venv` when a recent ``pip`` is available.

If you see errors like:

.. code-block:: text

    The virtual environment was not created successfully because ensurepip is not available.
    On Debian/Ubuntu systems, you need to install the python3-venv package.

this is the tool inside the tox environment hitting the missing system package, not tox itself.

**Solutions:**

- Install the system venv package: ``apt install python3-venv`` (or ``python3.X-venv`` for a specific version).
- Use :pypi:`tox-uv`, which replaces both the environment creation and package installation with :pypi:`uv`, avoiding
  the stdlib :mod:`venv` dependency entirely.

Misplaced configuration keys
============================

tox configuration is split into two sections: **core** (``[tox]`` / top-level TOML) and **environment** (``[testenv]`` /
``env_run_base`` in TOML). Options placed in the wrong section are silently ignored because tox cannot distinguish a
misplaced option from a plugin-defined key that isn't loaded yet (e.g. during provisioning).

To detect misplaced keys:

- Run ``tox run -v`` — unused keys are printed as warnings before the final report.
- Run ``tox config`` — unused keys appear as ``# !!! unused:`` comments per section.

For example, putting ``ignore_base_python_conflict`` in ``[testenv]`` instead of ``[tox]`` produces:

.. code-block:: text

    [testenv:py] unused config key(s): ignore_base_python_conflict

See the :ref:`Core <conf-core>` and :ref:`tox environment <conf-testenv>` reference sections for which options belong
where.

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
