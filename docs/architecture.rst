##############
 Architecture
##############

This guide walks through the internal architecture of ``tox`` — how the pieces fit together, what each subsystem does,
and where to look when contributing. It is aimed at **first-time contributors** and new team members.

*************
 Quick facts
*************

.. list-table::
    :widths: 25 75

    - - **Language**
      - Python ≥ 3.10
    - - **Build system**
      - hatchling (PEP 517/660)
    - - **Plugin framework**
      - pluggy
    - - **Test framework**
      - pytest (+ xdist, mock)
    - - **Docs**
      - Sphinx + Furo theme
    - - **License**
      - MIT

*******************
 Repository layout
*******************

::

    tox/
    ├── src/tox/                   # main package
    │   ├── run.py                 # entry point
    │   ├── provision.py           # self-provisioning logic
    │   ├── report.py              # logging / colored output
    │   ├── config/                # configuration subsystem
    │   │   ├── cli/               #   CLI parser (two-phase)
    │   │   ├── loader/            #   INI / TOML / memory loaders
    │   │   └── source/            #   config file discovery
    │   ├── session/               # runtime state + subcommands
    │   │   └── cmd/               #   built-in subcommands
    │   ├── tox_env/               # environment classes
    │   │   └── python/            #   Python-specific envs
    │   │       └── virtual_env/   #     virtualenv-based concrete envs
    │   ├── execute/               # subprocess execution
    │   ├── plugin/                # pluggy integration
    │   ├── journal/               # JSON result journal
    │   └── util/                  # helpers (graph, cpu, path, …)
    ├── tests/                     # mirrors src/tox/ structure
    └── docs/                      # Sphinx documentation

*************************
 High-level architecture
*************************

::

    ┌─────────────┐    ┌────────────────────────────┐
    │  CLI / argv  │───▶│  Two-Phase Parser (cli/)   │
    └─────────────┘    └─────────────┬──────────────┘
                                     │
                       ┌─────────────▼──────────────┐
                       │   Config (config/main.py)   │
                       │  Sources → Loaders → Types  │
                       └─────────────┬──────────────┘
                                     │
                       ┌─────────────▼──────────────┐
                       │  State (session/state.py)   │
                       │  owns Config + EnvSelector  │
                       └─────────────┬──────────────┘
                                     │
                       ┌─────────────▼──────────────┐
                       │  Provisioning (provision.py)│
                       │  ensures requires/min_ver   │
                       └─────────────┬──────────────┘
                                     │
                       ┌─────────────▼──────────────┐
                       │  Subcommand Handler         │
                       │  (run / list / config / …)  │
                       └─────────────┬──────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │         EnvSelector (env_select.py)  │
                  │  discovers + builds ToxEnv instances │
                  └────────┬──────────────────┬─────────┘
                           │                  │
              ┌────────────▼──────┐  ┌────────▼─────────┐
              │  RunToxEnv        │  │  PackageToxEnv    │
              │  (commands, deps) │  │  (wheel / sdist)  │
              └────────┬──────────┘  └──────────────────┘
                       │
              ┌────────▼──────────┐
              │  Execute          │
              │  (subprocess mgmt)│
              └───────────────────┘

.. _arch-entry-points:

********************
 Entry points & CLI
********************

Boot sequence
=============

All roads lead to ``tox.run:run()``:

.. code-block:: text

    tox.run:run()
        └── main(sys.argv[1:])
            ├── handler, state = setup_state(args)
            │   ├── get_options()          ← two-phase CLI parse
            │   └── State(options, args)   ← build runtime state
            ├── result = provision(state)  ← check requires / min_version
            │   └── if missing → re-invoke tox in a provisioned venv
            └── handler(state)             ← dispatch to subcommand

Two-phase CLI parsing
=====================

Phase 1 — *bootstrap* (before plugins load):

- Parses only ``-c`` / ``--conf`` (config path) and ``-v`` / ``-q`` (verbosity).
- Sets up logging (``setup_report``).
- Discovers configuration source (``discover_source``).
- Loads plugins (``MANAGER._setup()``).

Phase 2 — *full parse* (after plugins):

- Plugins register their arguments via the ``tox_add_option`` hook.
- Full ``argparse`` parse over all arguments.
- Subcommand handlers are stored in ``Parsed.cmd_handlers``.

Key classes
===========

- **ToxParser** — subclass of ``argparse.ArgumentParser``. Supports ``add_command()`` which creates a sub-parser and
  registers the handler.
- **Parsed** — the result of Phase 2. Holds ``options``, ``pos_args``, ``cmd_handlers``, ``env`` (a ``CliEnv``), and
  ``override`` (from ``-x``).
- **Options** — the argparse ``Namespace``. Notably has ``command`` (the chosen subcommand name).

Built-in subcommands
====================

.. list-table::
    :header-rows: 1

    - - Command
      - Alias
      - Module
      - Purpose
    - - ``run``
      - ``r``
      - ``session/cmd/run/sequential.py``
      - Run environments sequentially (default)
    - - ``run-parallel``
      - ``p``
      - ``session/cmd/run/parallel.py``
      - Run environments in parallel
    - - ``list``
      - ``l``
      - ``session/cmd/list_envs.py``
      - List available environments
    - - ``config``
      - ``c``
      - ``session/cmd/show_config.py``
      - Show materialised configuration
    - - ``devenv``
      - ``d``
      - ``session/cmd/devenv.py``
      - Create a development environment
    - - ``exec``
      - ``e``
      - ``session/cmd/exec_.py``
      - Run an arbitrary command in an env
    - - ``depends``
      - ``de``
      - ``session/cmd/depends.py``
      - Visualize environment dependency graph
    - - ``quickstart``
      - ``q``
      - ``session/cmd/quickstart.py``
      - Generate a starter tox config
    - - ``legacy``
      - ``le``
      - ``session/cmd/legacy.py``
      - Backward-compatible tox 3 entry point

.. _arch-configuration:

**********************
 Configuration system
**********************

The configuration system converts raw text (from INI/TOML files, CLI flags, and environment variables) into
strongly-typed Python objects.

Layer diagram
=============

::

    CLI Options (Parsed)
        │
        ▼
    Source (tox.ini / pyproject.toml / tox.toml / setup.cfg)
        │  provides Loaders per section
        ▼
    Config (main.py) — central registry of all ConfigSets
        │
        ▼
    ConfigSet (sets.py) — group of named config keys for one env/core
        │  uses
        ▼
    ConfigDefinition (of_type.py) — single key with type, default, post-process
        │  reads from
        ▼
    Loader (loader/api.py) — reads raw values from the source
        │  converts via
        ▼
    Convert / StrConvert (loader/convert.py, loader/str_convert.py)

Config
======

The central configuration object (``config/main.py``), created once per session:

- ``core`` property — lazily creates ``CoreConfigSet``, attaches loaders.
- ``get_env(name)`` — returns ``EnvConfigSet`` for a tox environment; resolves sections and base inheritance.
- ``memory_seed_loaders`` — ``defaultdict(list[MemoryLoader])``; inject config values programmatically.
- ``env_names()`` — iterates environment names from source + plugin-extended envs.

Source discovery
================

``discover_source()`` searches for configuration in this order:

1. If ``--conf`` is specified: use that file directly.
2. Otherwise, walk up from CWD looking for:

   - ``tox.toml`` → ``TomlSource``
   - ``pyproject.toml`` (with ``[tool.tox]``) → ``PyProjectTomlSource``
   - ``tox.ini`` → ``IniSource``
   - ``setup.cfg`` (with ``[tox:tox]``) → ``SetupCfgSource``

3. If nothing found: create an empty ``IniSource`` at CWD.

Source hierarchy:

::

    Source (ABC)                          # source/api.py
    ├── IniSource                         # source/ini.py
    │   └── SetupCfgSource                # source/setup_cfg.py
    └── TomlSource                        # source/toml_.py
        └── PyProjectTomlSource           # source/pyproject.py

Loaders
=======

.. list-table::
    :header-rows: 1

    - - Loader
      - Reads from
    - - ``IniLoader``
      - INI ``[section]`` key=value pairs
    - - ``TomlLoader``
      - TOML ``[table]`` key-value pairs
    - - ``MemoryLoader``
      - In-memory dict (provisioning, plugins)

How a value is resolved
=======================

When you access ``env_config["deps"]``:

1. ``ConfigDynamicDefinition.__call__()`` is invoked.
2. It checks its cache.
3. Iterates through the attached **loaders** (INI loader, TOML loader, memory loader).
4. The first loader that has the key returns the raw value.
5. The raw value is **converted** to the target type (via ``Convert``).
6. **Overrides** from ``--override`` are applied.
7. ``post_process`` callback runs (if registered).
8. The result is cached.

.. _arch-session:

****************************
 Session & state management
****************************

State
=====

``State`` (``session/state.py``) is the top-level runtime container:

.. list-table::
    :header-rows: 1

    - - Attribute
      - Type
      - Purpose
    - - ``conf``
      - ``Config``
      - Fully materialised tox configuration
    - - ``_options``
      - ``Parsed``
      - CLI parse result
    - - ``_args``
      - ``list[str]``
      - Original CLI args (re-invocation during provisioning)
    - - ``journal``
      - ``Journal``
      - Run journal for ``--result-json``
    - - ``envs``
      - ``EnvSelector``
      - Lazily created; single entry point for all env discovery

The ``envs`` property creates the ``EnvSelector`` on first access — typically when the subcommand handler starts
iterating environments.

CliEnv
======

``CliEnv`` captures the user's ``-e`` flag in three modes:

- **Specific list** (``-e py39,py310``) — run exactly these envs.
- **ALL** (``-e ALL``) — run every defined env.
- **Default** (no ``-e``) — use ``env_list`` from config.

EnvSelector
===========

The core environment discovery engine (``session/env_select.py``):

1. **Collect names** from config, CLI ``-e``, labels (``-m``), factors (``-f``).
2. **Phase 1**: For each name, build a ``ToxEnv`` via ``_build_run_env()``, then query its packaging needs and build
   package envs.
3. **Phase 2**: Reorder to match original definition order, apply label/factor filtering.
4. **Iterate**: ``iter()`` yields envs filtered by active status, run-env-only, and ``--skip-env`` regex.

Subcommand dispatch
===================

After provisioning, the handler is dispatched:

.. code-block:: python

    handler = state._options.cmd_handlers[state.conf.options.command]
    return handler(state)

Run execution uses ``ready_to_run_envs()`` for topological batch scheduling — environments whose ``depends`` are all
satisfied are yielded first.

.. _arch-environments:

******************
 Tox environments
******************

Class hierarchy
===============

::

    ToxEnv (ABC)                                       # tox_env/api.py
    │
    ├── RunToxEnv (ABC)                                # tox_env/runner.py
    │   └── PythonRun (Python + RunToxEnv, ABC)        # tox_env/python/runner.py
    │       └── VirtualEnvRunner (VirtualEnv + PythonRun)
    │                                                  # virtual_env/runner.py
    │                                                  # id = "virtualenv"
    │
    ├── PackageToxEnv (ABC)                            # tox_env/package.py
    │   └── PythonPackageToxEnv (Python + PackageToxEnv, ABC)
    │       ├── Pep517VenvPackager → Pep517VirtualEnvPackager
    │       │                                          # id = "virtualenv-pep-517"
    │       └── VenvCmdBuilder → VirtualEnvCmdBuilder
    │                                                  # id = "virtualenv-cmd-builder"
    │
    └── Python (ABC, mixin)                            # tox_env/python/api.py
        └── VirtualEnv (ABC, mixin)                    # virtual_env/api.py

**Diamond pattern**: Leaf classes combine a **role** (runner or packager) with an **implementation strategy**
(VirtualEnv). ``VirtualEnvRunner`` inherits from both ``VirtualEnv`` and ``PythonRun``.

Lifecycle
=========

::

    ┌──────────────────────────────────────┐
    │  1. SETUP                            │
    │  • Platform check (skip if no match) │
    │  • Recreate check → clean()          │
    │  • Create virtualenv                 │
    │  • Install deps                      │
    │  • Install package (build + install) │
    └──────────────┬───────────────────────┘
                   │
    ┌──────────────▼───────────────────────┐
    │  2. EXECUTE                          │
    │  • commands_pre                      │
    │  • commands                          │
    │  • commands_post (always runs)       │
    └──────────────┬───────────────────────┘
                   │
    ┌──────────────▼───────────────────────┐
    │  3. TEARDOWN                         │
    │  • Detach from package envs          │
    │  • Close PEP-517 backend             │
    │  • Delete built packages             │
    └──────────────────────────────────────┘

If a ``Recreate`` exception is raised during setup (e.g., Python version changed), tox automatically cleans and retries.

REGISTER singleton
==================

``REGISTER`` (``tox_env/register.py``) maintains two registries:

- ``_run_envs`` — runner types keyed by ``id()`` string.
- ``_package_envs`` — packager types keyed by ``id()`` string.
- ``default_env_runner`` — the first registered runner.

Plugins register new env types via the ``tox_register_tox_env`` hook.

Packaging
=========

A ``RunToxEnv`` determines if packaging is needed via ``package_envs``:

- Checks ``no_package`` / ``skip_install`` config.
- Returns ``(package_env_name, package_tox_env_type)`` tuples.

**Pep517VenvPackager** uses ``pyproject_api`` to communicate with the build backend (setuptools, flit, etc.) as a
subprocess. Supports sdist, wheel, editable (PEP-660), and editable-legacy builds.

**VenvCmdBuilder** runs user-defined commands to build packages.

Package envs are **thread-safe** — a single package env can serve multiple runners in parallel, guarded by ``filelock``.

Pip installer
=============

The concrete installer (``tox_env/python/pip/``):

- **Incremental installs**: compares new vs cached requirements, only installs changes.
- Supports ``pip_pre``, constraints, and ``use_frozen_constraints``.
- ``{packages}`` placeholder in ``install_command`` is replaced with actual arguments.

.. _arch-execution:

******************
 Execution system
******************

::

    Execute (ABC)                    # execute/api.py
    └── LocalSubProcessExecutor      # execute/local_sub_process/

Command flow
============

1. ``ToxEnv.execute(cmd, ...)`` builds an ``ExecuteRequest``.
2. ``Execute.call(request, ...)`` — context manager — creates ``SyncWrite`` streams for stdout/stderr.
3. ``ExecuteInstance.start(...)`` spawns a ``Popen`` subprocess and starts drain threads.
4. ``ExecuteStatus.wait()`` blocks until completion.
5. An ``Outcome`` is constructed with exit code, captured output, and timing.

Command resolution
==================

Before execution:

- Resolves the executable via ``shutil.which()`` using the env's ``PATH``.
- Checks against ``allowlist_externals`` glob patterns.
- On Unix, checks for ``TOX_LIMITED_SHEBANG`` and prepends the shebang interpreter.

Output capture
==============

``SyncWrite`` accumulates all bytes in a ``BytesIO`` (thread-safe):

- If ``show=True``, forwards to real stdout/stderr in real-time.
- Uses a 0.1s timer to flush partial lines.
- Stderr gets colored **red** when color is enabled.

Interrupt mechanism
===================

Escalating stop when tox receives a signal:

1. Wait ``cmd_kill_delay`` (default 0.0s) for voluntary exit.
2. Send ``SIGINT`` (Unix) / ``Ctrl+C`` (Windows), wait 0.3s.
3. Send ``SIGTERM``, wait 0.2s.
4. Send ``SIGKILL`` (Unix only), unconditional wait.

.. _arch-plugins:

***************
 Plugin system
***************

Tox uses `pluggy <https://pluggy.readthedocs.io/>`_ with the ``"tox"`` namespace.

Hooks
=====

.. list-table::
    :header-rows: 1

    - - Hook
      - When called
    - - ``tox_register_tox_env``
      - Register custom run/package env types
    - - ``tox_extend_env_list``
      - Declare additional env names dynamically
    - - ``tox_add_option``
      - Add CLI arguments (after logging + config discovery)
    - - ``tox_add_core_config``
      - Core configuration is being built
    - - ``tox_add_env_config``
      - Per-environment configuration is being built
    - - ``tox_before_run_commands``
      - Just before commands execute in an env
    - - ``tox_after_run_commands``
      - Just after commands execute
    - - ``tox_on_install``
      - Before executing an install command
    - - ``tox_env_teardown``
      - After an environment is torn down

Plugin loading sequence
=======================

::

    setup_report()           ← configure logging first
        │
    import plugin.manager    ← triggers MANAGER = ToxPluginManager()
        │
    MANAGER._setup()
        ├── 1. Load inline plugin (toxfile.py / ☣.py)
        ├── 2. Load external plugins (entry points)
        │      └── Respect TOX_DISABLED_EXTERNAL_PLUGINS env var
        ├── 3. Load internal plugins (16 hardcoded modules)
        └── 4. check_pending() — validate all hooks implemented

Inline plugins
==============

Tox searches the **parent directory** of the config file for ``toxfile.py`` or ``☣.py``. The first match wins. Example:

.. code-block:: python

    from tox.plugin import impl


    @impl
    def tox_add_option(parser):
        parser.add_argument("--my-flag", action="store_true")


    @impl
    def tox_add_env_config(env_conf, state):
        env_conf.add_config("my_key", of_type=str, default="", desc="My custom key")

External plugins
================

Any installed package declaring a ``tox`` entry point group is discovered:

.. code-block:: toml

    # In the plugin's pyproject.toml
    [project.entry-points.tox]
    my_plugin = "my_tox_plugin"

Set ``TOX_DISABLED_EXTERNAL_PLUGINS`` to a comma-separated list of plugin names to block specific plugins.

.. _arch-reporting:

*********************
 Reporting & logging
*********************

Verbosity levels
================

.. list-table::
    :header-rows: 1

    - - Verbosity
      - Flags
      - Log level
      - Output
    - - 0
      - ``-qq``
      - CRITICAL
      - Almost nothing
    - - 1
      - ``-q``
      - ERROR
      - Errors only
    - - **2**
      - *(default)*
      - **WARNING**
      - Normal output
    - - 3
      - ``-v``
      - INFO
      - Detailed progress
    - - 4
      - ``-vv``
      - DEBUG
      - Debug messages + timestamps
    - - 5
      - ``-vvv``
      - NOTSET
      - Everything

ToxHandler
==========

The central logging handler (``report.py``), added to the root logger:

- **Thread-local output** — each thread gets its own stdout/stderr via ``_LogThreadLocal``, enabling parallel execution
  to capture output separately.
- **Colored formatters** — Error = red, Warning = cyan, Info = white.
- **Per-environment context** — ``with_context(name)`` sets the current env name for the log prefix (magenta-coloured).
- **Command-echo pattern** — messages matching ``"%s%s> %s"`` get special color treatment (magenta env name, green
  ``>``, reset for command text).

Journal system
==============

Optional structured JSON output, enabled by ``--result-json <path>``:

- **Journal** (session level) — collects ``toxversion``, ``platform``, ``host``, and per-environment results.
- **EnvJournal** (per-environment) — records metadata and execution outcomes (command, stdout, stderr, exit code,
  elapsed time).

.. _arch-data-flow:

**********************
 End-to-end data flow
**********************

The following traces a ``tox run -e py311`` invocation from start to finish:

::

    ┌──────────────────────────────────────────────────────────┐
    │  1. ENTRY POINT                                          │
    │  run() → main()                                          │
    │  • setup_report()        ← configure logging             │
    │  • get_options()         ← two-phase CLI parse           │
    │  • setup_state()         ← build State(options, args)    │
    └──────────────────────────┬───────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────┐
    │  2. PROVISIONING                                         │
    │  • Check `requires` — are all deps installed?            │
    │  • Check `min_version` — is tox version sufficient?      │
    │  • If not → create .tox/.provision venv → re-invoke tox  │
    │  • If OK → continue                                      │
    └──────────────────────────┬───────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────┐
    │  3. DISPATCH                                             │
    │  handler = cmd_handlers[options.command]                  │
    │  handler(state)          ← calls run_command(state)      │
    └──────────────────────────┬───────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────┐
    │  4. ENVIRONMENT DISCOVERY                                │
    │  state.envs._defined_envs  ← lazy property triggers     │
    │  • _collect_names()  ← from config, CLI, labels          │
    │  • Phase 1: _build_run_env() + _build_pkg_env()          │
    │  • Phase 2: reorder, apply filters                       │
    └──────────────────────────┬───────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────┐
    │  5. RUN ENVIRONMENT                                      │
    │  a. SETUP — create virtualenv, install deps + package    │
    │  b. EXECUTE — commands_pre → commands → commands_post    │
    │  c. TEARDOWN — detach from pkgs, close backends          │
    └──────────────────────────┬───────────────────────────────┘
                               │
    ┌──────────────────────────▼───────────────────────────────┐
    │  7. RESULT                                               │
    │  • Collect outcomes per env                              │
    │  • Write journal (--result-json)                         │
    │  • Report summary                                        │
    │  • Return exit code (0 = all passed)                     │
    └──────────────────────────────────────────────────────────┘

Key decision points
===================

.. list-table::
    :header-rows: 1

    - - Point
      - Decision
      - Outcome
    - - Provisioning
      - Are ``requires`` satisfied?
      - Continue or re-invoke in venv
    - - Platform check
      - Does ``platform`` regex match?
      - Run or skip env
    - - Recreate
      - Config changed since last run?
      - Wipe and rebuild, or reuse
    - - Package
      - ``skip_install`` / ``no_package``?
      - Build and install, or skip
    - - Command prefix
      - ``!`` or ``-`` prefix?
      - Invert or ignore exit code
    - - Interrupt
      - Signal received?
      - Escalate: INT → TERM → KILL

.. _arch-testing:

***************
 Testing guide
***************

The ``tests/`` directory **mirrors** ``src/tox/``:

::

    tests/
    ├── conftest.py                    # Root fixtures
    ├── config/                        # ← mirrors src/tox/config/
    │   ├── cli/
    │   ├── loader/
    │   └── source/
    ├── execute/                       # ← mirrors src/tox/execute/
    ├── journal/
    ├── plugin/
    ├── session/
    │   └── cmd/                       # Subcommand tests
    ├── tox_env/
    │   └── python/
    ├── util/
    ├── demo_pkg_inline/               # Minimal PEP-517 test package
    └── demo_pkg_setuptools/           # Setuptools test package

Key fixtures
============

- **tox_project** — creates a temporary project with a tox config and runs tox against it. The most important
  integration test fixture.
- **demo_pkg_inline** — minimal PEP-517 package with a custom build backend.
- **demo_pkg_setuptools** — setuptools-based package for setuptools-specific tests.

*****************
 Design patterns
*****************

.. list-table::
    :header-rows: 1

    - - Pattern
      - Where
    - - **Lazy properties**
      - ``State.envs``, ``Config.core``, ``EnvSelector._defined_envs``
    - - **Two-phase init**
      - CLI parsing (bootstrap then full), env build (run then package)
    - - **Plugin hooks at every seam**
      - Config, env setup, install, commands, teardown
    - - **Abstract base + mixins**
      - ``ToxEnv`` hierarchy (diamond MRO)
    - - **Registry / singleton**
      - ``REGISTER`` for env types, ``MANAGER`` for plugins
    - - **Thread-local state**
      - ``ToxHandler``'s ``_LogThreadLocal`` for per-env output
    - - **Incremental caching**
      - ``CacheToxInfo`` (``.tox-info.json``), pip installer diff

***************************
 Recommended reading order
***************************

For a first-time contributor:

1. ``src/tox/run.py`` — entry point (~50 lines)
2. ``src/tox/session/state.py`` — state construction
3. ``src/tox/provision.py`` — provisioning logic
4. ``src/tox/session/env_select.py`` — env discovery
5. ``src/tox/tox_env/api.py`` — base environment
6. ``src/tox/execute/api.py`` — execution framework
7. ``src/tox/config/main.py`` — configuration
