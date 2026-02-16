###########
 Onboarder
###########

This guide walks through tox's internal architecture — how the pieces fit together, what each subsystem does, and where
to look when contributing. It is aimed at **first-time contributors** and new team members.

**How to use this guide:**

- **Part 1** gives you the big picture and tells you where to start reading code.
- **Part 2** follows tox's execution flow from startup to completion.
- **Part 3** covers supporting systems you'll need when working on specific features.
- **Part 4** contains reference materials for looking up details.

**********************
 Part 1: Get Oriented
**********************

Quick facts
===========

.. list-table::
    :widths: 25 75

    - - **Language**
      - `Python <https://www.python.org/>`_ ≥ 3.10
    - - **Build system**
      - `hatchling <https://hatch.pypa.io/latest/config/build/>`_ (`PEP 517 <https://peps.python.org/pep-0517/>`_ / `PEP
        660 <https://peps.python.org/pep-0660/>`_)
    - - **Plugin framework**
      - `pluggy <https://pluggy.readthedocs.io/>`_
    - - **Test framework**
      - `pytest <https://pytest.org/>`_ (+ `xdist <https://pytest-xdist.readthedocs.io/>`_, `pytest-mock
        <https://pytest-mock.readthedocs.io/>`_)
    - - **Docs**
      - `Sphinx <https://www.sphinx-doc.org/>`_ + `Furo <https://github.com/pradyunsg/furo>`_ theme
    - - **License**
      - `MIT <https://opensource.org/licenses/MIT>`_

Repository layout
=================

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

Start here: Recommended reading order
=====================================

For a first-time contributor, read the code in this order:

1. `src/tox/run.py <https://github.com/tox-dev/tox/blob/main/src/tox/run.py>`_ — entry point (~50 lines)
2. `src/tox/session/state.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/state.py>`_ — state construction
3. `src/tox/provision.py <https://github.com/tox-dev/tox/blob/main/src/tox/provision.py>`_ — provisioning logic
4. `src/tox/session/env_select.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/env_select.py>`_ — env
   discovery
5. `src/tox/tox_env/api.py <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/api.py>`_ — base environment
6. `src/tox/execute/api.py <https://github.com/tox-dev/tox/blob/main/src/tox/execute/api.py>`_ — execution framework
7. `src/tox/config/main.py <https://github.com/tox-dev/tox/blob/main/src/tox/config/main.py>`_ — configuration

The big picture: End-to-end flow
================================

This traces ``tox run -e py311`` from start to finish, showing the six main phases:

.. mermaid::

    flowchart LR
        subgraph ENTRY["1️⃣ ENTRY POINT"]
            direction TB
            A[tox run -e py311]
            B[Parse CLI]
            C[Load config]
            D[Build State]
            A --> B --> C --> D
        end

        subgraph PROV["2️⃣ PROVISIONING"]
            direction TB
            E{Requirements<br/>satisfied?}
            F[Create provision env]
            G[Re-invoke tox]
            E -->|No| F --> G
        end

        subgraph DISC["3️⃣ DISCOVERY"]
            direction TB
            H[Dispatch subcommand]
            I[Discover envs]
            J[Resolve dependencies]
            H --> I --> J
        end

        subgraph SETUP["4️⃣ ENVIRONMENT SETUP"]
            direction TB
            K{Virtualenv<br/>exists?}
            L[Create virtualenv]
            M[Install dependencies]
            N[Build & install package]
            K -->|No| L --> M
            K -->|Yes| M
            M --> N
        end

        subgraph EXEC["5️⃣ EXECUTION"]
            direction TB
            O[Run commands_pre]
            P[Run commands]
            Q[Run commands_post]
            O --> P --> Q
        end

        subgraph RESULT["6️⃣ RESULTS"]
            direction TB
            R[Collect outcomes]
            S[Write journal]
            T[Report summary]
            R --> S --> T
        end

        ENTRY --> PROV
        G -.Re-invoke.-> ENTRY
        PROV -->|Yes| DISC
        DISC --> SETUP
        SETUP --> EXEC
        EXEC --> RESULT

        style ENTRY fill:#E8F5E9,stroke:#4CAF50,stroke-width:2px
        style PROV fill:#FFF3E0,stroke:#FF9800,stroke-width:2px
        style DISC fill:#E3F2FD,stroke:#2196F3,stroke-width:2px
        style SETUP fill:#F3E5F5,stroke:#9C27B0,stroke-width:2px
        style EXEC fill:#E1F5FE,stroke:#03A9F4,stroke-width:2px
        style RESULT fill:#FFEBEE,stroke:#F44336,stroke-width:2px

        style A fill:#5CB85C,stroke:#3D8B40,color:#fff
        style B fill:#5CB85C,stroke:#3D8B40,color:#fff
        style C fill:#5CB85C,stroke:#3D8B40,color:#fff
        style D fill:#5CB85C,stroke:#3D8B40,color:#fff
        style E fill:#F0AD4E,stroke:#C88A3C,color:#fff
        style F fill:#F0AD4E,stroke:#C88A3C,color:#fff
        style G fill:#F0AD4E,stroke:#C88A3C,color:#fff
        style H fill:#4A90E2,stroke:#2E5C8A,color:#fff
        style I fill:#4A90E2,stroke:#2E5C8A,color:#fff
        style J fill:#4A90E2,stroke:#2E5C8A,color:#fff
        style K fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style L fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style M fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style N fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style O fill:#3498DB,stroke:#2574A9,color:#fff
        style P fill:#3498DB,stroke:#2574A9,color:#fff
        style Q fill:#3498DB,stroke:#2574A9,color:#fff
        style R fill:#E74C3C,stroke:#B23A2F,color:#fff
        style S fill:#E74C3C,stroke:#B23A2F,color:#fff
        style T fill:#E74C3C,stroke:#B23A2F,color:#fff

High-level architecture
=======================

The following diagram shows the main flow through tox's subsystems:

.. mermaid::

    flowchart TD
        A[CLI / argv]
        B[Two-Phase Parser<br/>cli/]
        C[Config<br/>config/main.py<br/>Sources → Loaders → Types]
        D[State<br/>session/state.py<br/>owns Config + EnvSelector]
        E[Provisioning<br/>provision.py<br/>ensures requires/min_ver]
        F[Subcommand Handler<br/>run / list / config / …]
        G[EnvSelector<br/>env_select.py<br/>discovers + builds ToxEnv instances]
        H[RunToxEnv<br/>commands, deps]
        I[PackageToxEnv<br/>wheel / sdist]
        J[Execute<br/>subprocess mgmt]

        A --> B --> C --> D --> E --> F --> G
        G --> H
        G --> I
        H --> J

        style A fill:#E74C3C,stroke:#B23A2F,color:#fff
        style B fill:#5CB85C,stroke:#3D8B40,color:#fff
        style C fill:#4A90E2,stroke:#2E5C8A,color:#fff
        style D fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style E fill:#F0AD4E,stroke:#C88A3C,color:#fff
        style F fill:#E67E22,stroke:#B85E18,color:#fff
        style G fill:#3498DB,stroke:#2574A9,color:#fff
        style H fill:#27AE60,stroke:#1E8449,color:#fff
        style I fill:#16A085,stroke:#117864,color:#fff
        style J fill:#C0392B,stroke:#943126,color:#fff

*****************************
 Part 2: Main Execution Flow
*****************************

This section follows the chronological execution path through tox, from startup to completion.

.. _exec-boot-sequence:

Boot sequence
=============

All roads lead to `tox.run.run() <https://github.com/tox-dev/tox/blob/main/src/tox/run.py>`_:

.. mermaid::

    flowchart TD
        A[run]
        B[main]
        C[setup_report]
        D[get_options]
        E[setup_state]
        F{provision check?}
        G[Create provision env]
        H[handler]

        A --> B --> C --> D --> E --> F
        F -->|Missing| G
        F -->|OK| H
        G -.Re-invoke.-> A

        style A fill:#5CB85C,stroke:#3D8B40,color:#fff
        style B fill:#5CB85C,stroke:#3D8B40,color:#fff
        style C fill:#5CB85C,stroke:#3D8B40,color:#fff
        style D fill:#4A90E2,stroke:#2E5C8A,color:#fff
        style E fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style F fill:#F0AD4E,stroke:#C88A3C,color:#fff
        style G fill:#E67E22,stroke:#B85E18,color:#fff
        style H fill:#3498DB,stroke:#2574A9,color:#fff

.. _exec-entry-points:

Entry points & CLI
==================

The CLI parsing and command dispatch system handles argument processing, plugin loading, and routing to subcommands.

Two-phase CLI parsing
---------------------

Phase 1 — *bootstrap* (before plugins load):

- It parses only ``-c`` / ``--conf`` (config path) and ``-v`` / ``-q`` (verbosity).
- It sets up logging (see :ref:`sys-reporting`).
- It discovers configuration source (see :ref:`sys-configuration`).
- It loads plugins (see :ref:`sys-plugins`).

Phase 2 — *full parse* (after plugins):

- Plugins register their arguments via the ``tox_add_option`` hook (see :ref:`sys-plugins`).
- It performs a full ``argparse`` parse over all arguments.
- Subcommand handlers are stored in ``Parsed.cmd_handlers``.

Key classes
-----------

- `ToxParser <https://github.com/tox-dev/tox/blob/main/src/tox/config/cli/parser.py>`_ — subclass of
  :class:`argparse.ArgumentParser`. Supports ``add_command()`` which creates a sub-parser and registers the handler.
- `Parsed <https://github.com/tox-dev/tox/blob/main/src/tox/config/cli/parse.py>`_ — the result of Phase 2. Holds
  ``options``, ``pos_args``, ``cmd_handlers``, ``env`` (a ``CliEnv``), and ``override`` (from ``-x``).
- **Options** — the :class:`argparse.Namespace`. Notably has ``command`` (the chosen subcommand name).

Built-in subcommands
--------------------

.. list-table::
    :header-rows: 1

    - - Command
      - Alias
      - Module
      - Purpose
    - - ``run``
      - ``r``
      - `session/cmd/run/sequential.py
        <https://github.com/tox-dev/tox/blob/main/src/tox/session/cmd/run/sequential.py>`_
      - Run environments sequentially (default)
    - - ``run-parallel``
      - ``p``
      - `session/cmd/run/parallel.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/cmd/run/parallel.py>`_
      - Run environments in parallel
    - - ``list``
      - ``l``
      - `session/cmd/list_envs.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/cmd/list_envs.py>`_
      - List available environments
    - - ``config``
      - ``c``
      - `session/cmd/show_config.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/cmd/show_config.py>`_
      - Show materialised configuration
    - - ``devenv``
      - ``d``
      - `session/cmd/devenv.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/cmd/devenv.py>`_
      - Create a development environment
    - - ``exec``
      - ``e``
      - `session/cmd/exec_.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/cmd/exec_.py>`_
      - Run an arbitrary command in an env
    - - ``depends``
      - ``de``
      - `session/cmd/depends.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/cmd/depends.py>`_
      - Visualize environment dependency graph
    - - ``quickstart``
      - ``q``
      - `session/cmd/quickstart.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/cmd/quickstart.py>`_
      - Generate a starter tox config
    - - ``legacy``
      - ``le``
      - `session/cmd/legacy.py <https://github.com/tox-dev/tox/blob/main/src/tox/session/cmd/legacy.py>`_
      - Backward-compatible tox 3 entry point

.. _exec-session:

Session & state management
==========================

State
-----

`State <https://github.com/tox-dev/tox/blob/main/src/tox/session/state.py>`_ is the top-level runtime container:

.. list-table::
    :header-rows: 1

    - - Attribute
      - Type
      - Purpose
    - - ``conf``
      - `Config <https://github.com/tox-dev/tox/blob/main/src/tox/config/main.py>`_
      - Fully materialised tox configuration
    - - ``_options``
      - `Parsed <https://github.com/tox-dev/tox/blob/main/src/tox/config/cli/parse.py>`_
      - CLI parse result
    - - ``_args``
      - ``list[str]``
      - Original CLI args (re-invocation during provisioning)
    - - ``journal``
      - `Journal <https://github.com/tox-dev/tox/blob/main/src/tox/journal/__init__.py>`_
      - Run journal for ``--result-json``
    - - ``envs``
      - `EnvSelector <https://github.com/tox-dev/tox/blob/main/src/tox/session/env_select.py>`_
      - Lazily created; single entry point for all env discovery

The ``envs`` property creates the `EnvSelector
<https://github.com/tox-dev/tox/blob/main/src/tox/session/env_select.py>`_ on first access — typically when the
subcommand handler starts iterating environments.

CliEnv
------

`CliEnv <https://github.com/tox-dev/tox/blob/main/src/tox/config/cli/env.py>`_ captures the user's ``-e`` flag in three
modes:

- **Specific list** (``-e py39,py310``) — run exactly these envs.
- **ALL** (``-e ALL``) — run every defined env.
- **Default** (no ``-e``) — use ``env_list`` from config.

EnvSelector
-----------

The core environment discovery engine `EnvSelector
<https://github.com/tox-dev/tox/blob/main/src/tox/session/env_select.py>`_:

1. **Collect names** from config, CLI ``-e``, labels (``-m``), factors (``-f``).
2. **Phase 1**: For each name, build a :class:`~tox.tox_env.api.ToxEnv` via ``_build_run_env()``, then query its
   packaging needs and build package envs.
3. **Phase 2**: Reorder to match original definition order, apply label/factor filtering.
4. **Iterate**: ``iter()`` yields envs filtered by active status, run-env-only, and ``--skip-env`` regex.

Subcommand dispatch
-------------------

After provisioning, the handler is dispatched (see :ref:`exec-entry-points` for built-in subcommands):

.. code-block:: python

    handler = state._options.cmd_handlers[state.conf.options.command]
    return handler(state)

Run execution uses ``ready_to_run_envs()`` for topological batch scheduling — environments whose ``depends`` are all
satisfied are yielded first.

.. _exec-environment-lifecycle:

Environment lifecycle
=====================

.. mermaid::

    flowchart TD
        A["1. SETUP<br/>• Platform check (skip if no match)<br/>• Recreate check → clean()<br/>• Create virtualenv<br/>• Install deps<br/>• Install package (build + install)"]
        B["2. EXECUTE<br/>• commands_pre<br/>• commands<br/>• commands_post (always runs)"]
        C["3. TEARDOWN<br/>• Detach from package envs<br/>• Close PEP-517 backend<br/>• Delete built packages"]

        A --> B --> C

        style A fill:#5CB85C,stroke:#3D8B40,color:#fff
        style B fill:#F0AD4E,stroke:#C88A3C,color:#fff
        style C fill:#E74C3C,stroke:#B23A2F,color:#fff

If a `Recreate <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/errors.py>`_ exception is raised during setup
(e.g., Python version changed), tox automatically cleans and retries.

.. _exec-execution:

Execution system
================

.. mermaid::

    flowchart TD
        A["Execute (ABC)<br/>execute/api.py"]
        B["LocalSubProcessExecutor<br/>execute/local_sub_process/"]

        A --> B

        style A fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style B fill:#4A90E2,stroke:#2E5C8A,color:#fff

Command flow
------------

1. :meth:`ToxEnv.execute() <tox.tox_env.api.ToxEnv.execute>` builds an `ExecuteRequest
   <https://github.com/tox-dev/tox/blob/main/src/tox/execute/request.py>`_.
2. `Execute.call() <https://github.com/tox-dev/tox/blob/main/src/tox/execute/api.py>`_ — context manager — creates
   `SyncWrite <https://github.com/tox-dev/tox/blob/main/src/tox/execute/stream.py>`_ streams for stdout/stderr.
3. `ExecuteInstance.start()
   <https://github.com/tox-dev/tox/blob/main/src/tox/execute/local_sub_process/execute_instance.py>`_ spawns a
   :class:`subprocess.Popen` subprocess and starts drain threads.
4. `ExecuteStatus.wait()
   <https://github.com/tox-dev/tox/blob/main/src/tox/execute/local_sub_process/execute_status.py>`_ blocks until
   completion.
5. An `Outcome <https://github.com/tox-dev/tox/blob/main/src/tox/execute/request.py>`_ is constructed with exit code,
   captured output, and timing.

Command resolution
------------------

Before execution, tox performs the following steps:

- It resolves the executable via :func:`shutil.which` using the env's ``PATH``.
- It checks against ``allowlist_externals`` glob patterns.
- On Unix, it checks for ``TOX_LIMITED_SHEBANG`` and prepends the shebang interpreter.

Output capture
--------------

The `SyncWrite <https://github.com/tox-dev/tox/blob/main/src/tox/execute/stream.py>`_ class accumulates all bytes in a
:class:`io.BytesIO` buffer (thread-safe):

- If ``show=True``, it forwards to real stdout/stderr in real-time.
- It uses a 0.1s timer to flush partial lines.
- Stderr gets colored **red** when color is enabled.

Interrupt mechanism
-------------------

Escalating stop when tox receives a signal:

1. Wait ``cmd_kill_delay`` (default 0.0s) for voluntary exit.
2. Send ``SIGINT`` (Unix) / ``Ctrl+C`` (Windows), wait 0.3s.
3. Send ``SIGTERM``, wait 0.2s.
4. Send ``SIGKILL`` (Unix only), unconditional wait.

****************************
 Part 3: Supporting Systems
****************************

These subsystems support the main execution flow. Read these when working on specific features.

.. _sys-configuration:

Configuration system
====================

The configuration system converts raw text (from INI/TOML files, CLI flags, and environment variables) into
strongly-typed Python objects.

Layer diagram
-------------

.. mermaid::

    flowchart TD
        A[CLI Options<br/>Parsed]
        B[Source<br/>tox.ini / pyproject.toml / tox.toml / setup.cfg<br/>provides Loaders per section]
        C[Config<br/>main.py<br/>central registry of all ConfigSets]
        D[ConfigSet<br/>sets.py<br/>group of named config keys for one env/core]
        E[ConfigDefinition<br/>of_type.py<br/>single key with type, default, post-process]
        F[Loader<br/>loader/api.py<br/>reads raw values from the source]
        G[Convert / StrConvert<br/>loader/convert.py, loader/str_convert.py]

        A --> B
        B --> C
        C --> D
        D --> E
        E --> F
        F --> G

        style A fill:#4A90E2,stroke:#2E5C8A,color:#fff
        style B fill:#5CB85C,stroke:#3D8B40,color:#fff
        style C fill:#F0AD4E,stroke:#C88A3C,color:#fff
        style D fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style E fill:#E67E22,stroke:#B85E18,color:#fff
        style F fill:#3498DB,stroke:#2574A9,color:#fff
        style G fill:#E74C3C,stroke:#B23A2F,color:#fff

Config
------

The central `Config <https://github.com/tox-dev/tox/blob/main/src/tox/config/main.py>`_ object is created once per
session:

- The ``core`` property lazily creates `CoreConfigSet
  <https://github.com/tox-dev/tox/blob/main/src/tox/config/sets.py>`_ and attaches loaders.
- The ``get_env(name)`` method returns `EnvConfigSet <https://github.com/tox-dev/tox/blob/main/src/tox/config/sets.py>`_
  for a tox environment and resolves sections and base inheritance.
- The ``memory_seed_loaders`` is a ``defaultdict(list[MemoryLoader])`` that injects config values programmatically.
- The ``env_names()`` method iterates environment names from source and plugin-extended envs.

Source discovery
----------------

The `discover_source() <https://github.com/tox-dev/tox/blob/main/src/tox/config/source/discover.py>`_ function searches
for configuration in this order:

1. If ``--conf`` is specified, it uses that file directly.
2. Otherwise, it walks up from CWD looking for:

   - ``tox.toml`` which uses `TomlSource <https://github.com/tox-dev/tox/blob/main/src/tox/config/source/toml_.py>`_.
   - ``pyproject.toml`` (with ``[tool.tox]``) which uses `PyProjectTomlSource
     <https://github.com/tox-dev/tox/blob/main/src/tox/config/source/pyproject.py>`_.
   - ``tox.ini`` which uses `IniSource <https://github.com/tox-dev/tox/blob/main/src/tox/config/source/ini.py>`_.
   - ``setup.cfg`` (with ``[tox:tox]``) which uses `SetupCfgSource
     <https://github.com/tox-dev/tox/blob/main/src/tox/config/source/setup_cfg.py>`_.

3. If nothing is found, it creates an empty `IniSource
   <https://github.com/tox-dev/tox/blob/main/src/tox/config/source/ini.py>`_ at CWD.

Source hierarchy:

.. mermaid::

    flowchart TD
        A["Source (ABC)<br/>source/api.py"]
        B["IniSource<br/>source/ini.py"]
        C["SetupCfgSource<br/>source/setup_cfg.py"]
        D["TomlSource<br/>source/toml_.py"]
        E["PyProjectTomlSource<br/>source/pyproject.py"]

        A --> B
        A --> D
        B --> C
        D --> E

        style A fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style B fill:#4A90E2,stroke:#2E5C8A,color:#fff
        style C fill:#3498DB,stroke:#2574A9,color:#fff
        style D fill:#5CB85C,stroke:#3D8B40,color:#fff
        style E fill:#27AE60,stroke:#1E8449,color:#fff

Loaders
-------

.. list-table::
    :header-rows: 1

    - - Loader
      - Reads from
    - - `IniLoader <https://github.com/tox-dev/tox/blob/main/src/tox/config/loader/ini.py>`_
      - INI ``[section]`` key=value pairs
    - - `TomlLoader <https://github.com/tox-dev/tox/blob/main/src/tox/config/loader/toml.py>`_
      - TOML ``[table]`` key-value pairs
    - - `MemoryLoader <https://github.com/tox-dev/tox/blob/main/src/tox/config/loader/memory.py>`_
      - In-memory dict (provisioning, plugins)

How a value is resolved
-----------------------

When you access ``env_config["deps"]``:

1. `ConfigDynamicDefinition.__call__() <https://github.com/tox-dev/tox/blob/main/src/tox/config/of_type.py>`_ is
   invoked.
2. It checks its cache.
3. Iterates through the attached **loaders** (INI loader, TOML loader, memory loader).
4. The first loader that has the key returns the raw value.
5. The raw value is **converted** to the target type (via `Convert
   <https://github.com/tox-dev/tox/blob/main/src/tox/config/loader/convert.py>`_).
6. **Overrides** from ``--override`` are applied.
7. ``post_process`` callback runs (if registered).
8. The result is cached.

.. _sys-plugins:

Plugin system
=============

Tox uses `pluggy <https://pluggy.readthedocs.io/>`_ with the ``"tox"`` namespace.

Hooks
-----

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
-----------------------

.. mermaid::

    flowchart TD
        A["setup_report()<br/>configure logging first"]
        B["import plugin.manager<br/>triggers MANAGER = ToxPluginManager()"]
        C["MANAGER._setup()"]
        D["1. Load inline plugin<br/>toxfile.py / ☣.py"]
        E["2. Load external plugins<br/>entry points"]
        F["Respect TOX_DISABLED_EXTERNAL_PLUGINS<br/>env var"]
        G["3. Load internal plugins<br/>16 hardcoded modules"]
        H["4. check_pending()<br/>validate all hooks implemented"]

        A --> B --> C
        C --> D
        C --> E
        E --> F
        C --> G
        C --> H

        style A fill:#5CB85C,stroke:#3D8B40,color:#fff
        style B fill:#4A90E2,stroke:#2E5C8A,color:#fff
        style C fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style D fill:#F0AD4E,stroke:#C88A3C,color:#fff
        style E fill:#E67E22,stroke:#B85E18,color:#fff
        style F fill:#D35400,stroke:#A04000,color:#fff
        style G fill:#3498DB,stroke:#2574A9,color:#fff
        style H fill:#E74C3C,stroke:#B23A2F,color:#fff

Inline plugins
--------------

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
----------------

Any installed package declaring a ``tox`` entry point group is discovered:

.. code-block:: toml

    # In the plugin's pyproject.toml
    [project.entry-points.tox]
    my_plugin = "my_tox_plugin"

Set ``TOX_DISABLED_EXTERNAL_PLUGINS`` to a comma-separated list of plugin names to block specific plugins.

Packaging details
=================

REGISTER singleton
------------------

The `REGISTER <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/register.py>`_ singleton maintains two
registries:

- ``_run_envs`` stores runner types keyed by ``id()`` string.
- ``_package_envs`` stores packager types keyed by ``id()`` string.
- ``default_env_runner`` holds the first registered runner.

Plugins register new env types via the ``tox_register_tox_env`` hook (see :ref:`sys-plugins`).

Package environment
-------------------

A :class:`~tox.tox_env.runner.RunToxEnv` determines if packaging is needed via ``package_envs``:

- It checks ``no_package`` / ``skip_install`` config.
- It returns ``(package_env_name, package_tox_env_type)`` tuples.

The `Pep517VenvPackager <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/python/package.py>`_ uses
`pyproject_api <https://pyproject-api.readthedocs.io/>`_ to communicate with the build backend (setuptools, flit, etc.)
as a subprocess. It supports sdist, wheel, editable (PEP-660), and editable-legacy builds.

The `VenvCmdBuilder <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/python/package.py>`_ runs user-defined
commands to build packages.

Package envs are **thread-safe**, meaning a single package env can serve multiple runners in parallel, guarded by
``filelock``.

Pip installer
-------------

The concrete installer (`tox_env/python/pip/ <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/python/pip/>`_)
has the following features:

- **Incremental installs** compare new vs cached requirements and only install changes.
- It supports ``pip_pre``, constraints, and ``use_frozen_constraints``.
- The ``{packages}`` placeholder in ``install_command`` is replaced with actual arguments.
- See :ref:`exec-execution` for how installation commands are executed.

.. _sys-reporting:

Reporting & logging
===================

Verbosity levels
----------------

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
----------

The central logging handler `ToxHandler <https://github.com/tox-dev/tox/blob/main/src/tox/report.py>`_ is added to the
root logger and provides:

- **Thread-local output** where each thread gets its own stdout/stderr via ``_LogThreadLocal``, enabling parallel
  execution to capture output separately.
- **Colored formatters** where Error = red, Warning = cyan, Info = white.
- **Per-environment context** where ``with_context(name)`` sets the current env name for the log prefix
  (magenta-coloured).
- **Command-echo pattern** where messages matching ``"%s%s> %s"`` get special color treatment (magenta env name, green
  ``>``, reset for command text).

Journal system
--------------

Optional structured JSON output is enabled by ``--result-json <path>``:

- `Journal <https://github.com/tox-dev/tox/blob/main/src/tox/journal/__init__.py>`_ (session level) collects
  ``toxversion``, ``platform``, ``host``, and per-environment results.
- `EnvJournal <https://github.com/tox-dev/tox/blob/main/src/tox/journal/env.py>`_ (per-environment) records metadata and
  execution outcomes (command, stdout, stderr, exit code, elapsed time).

*****************************
 Part 4: Reference Materials
*****************************

Class hierarchies
=================

ToxEnv hierarchy
----------------

.. mermaid::

    flowchart TD
        A["ToxEnv (ABC)<br/>tox_env/api.py"]
        B["RunToxEnv (ABC)<br/>tox_env/runner.py"]
        C["PythonRun<br/>Python + RunToxEnv (ABC)<br/>tox_env/python/runner.py"]
        D["VirtualEnvRunner<br/>VirtualEnv + PythonRun<br/>virtual_env/runner.py<br/>id = virtualenv"]
        E["PackageToxEnv (ABC)<br/>tox_env/package.py"]
        F["PythonPackageToxEnv<br/>Python + PackageToxEnv (ABC)"]
        G["Pep517VirtualEnvPackager<br/>id = virtualenv-pep-517"]
        H["VirtualEnvCmdBuilder<br/>id = virtualenv-cmd-builder"]
        I["Python (ABC, mixin)<br/>tox_env/python/api.py"]
        J["VirtualEnv (ABC, mixin)<br/>virtual_env/api.py"]

        A --> B
        A --> E
        A --> I
        B --> C
        C --> D
        E --> F
        F --> G
        F --> H
        I --> J

        style A fill:#9B59B6,stroke:#6D3F8C,color:#fff
        style B fill:#4A90E2,stroke:#2E5C8A,color:#fff
        style C fill:#3498DB,stroke:#2574A9,color:#fff
        style D fill:#27AE60,stroke:#1E8449,color:#fff
        style E fill:#F0AD4E,stroke:#C88A3C,color:#fff
        style F fill:#E67E22,stroke:#B85E18,color:#fff
        style G fill:#5CB85C,stroke:#3D8B40,color:#fff
        style H fill:#16A085,stroke:#117864,color:#fff
        style I fill:#E74C3C,stroke:#B23A2F,color:#fff
        style J fill:#C0392B,stroke:#943126,color:#fff

The **diamond pattern** means that leaf classes combine a **role** (runner or packager) with an **implementation
strategy** (`VirtualEnv <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/python/virtual_env/api.py>`_). For
example, `VirtualEnvRunner <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/python/virtual_env/runner.py>`_
inherits from both `VirtualEnv <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/python/virtual_env/api.py>`_
and `PythonRun <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/python/runner.py>`_.

Design patterns
===============

.. list-table::
    :header-rows: 1

    - - Pattern
      - Where
    - - **Lazy properties**
      - `State.envs <https://github.com/tox-dev/tox/blob/main/src/tox/session/state.py>`_, `Config.core
        <https://github.com/tox-dev/tox/blob/main/src/tox/config/main.py>`_, `EnvSelector._defined_envs
        <https://github.com/tox-dev/tox/blob/main/src/tox/session/env_select.py>`_
    - - **Two-phase init**
      - CLI parsing (bootstrap then full), env build (run then package)
    - - **Plugin hooks at every seam**
      - Config, env setup, install, commands, teardown
    - - **Abstract base + mixins**
      - :class:`~tox.tox_env.api.ToxEnv` hierarchy (diamond MRO)
    - - **Registry / singleton**
      - `REGISTER <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/register.py>`_ for env types, `MANAGER
        <https://github.com/tox-dev/tox/blob/main/src/tox/plugin/manager.py>`_ for plugins
    - - **Thread-local state**
      - `ToxHandler <https://github.com/tox-dev/tox/blob/main/src/tox/report.py>`_'s ``_LogThreadLocal`` for per-env
        output
    - - **Incremental caching**
      - `CacheToxInfo <https://github.com/tox-dev/tox/blob/main/src/tox/tox_env/info.py>`_ (``.tox-info.json``), pip
        installer diff

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

Testing guide
=============

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
------------

- **tox_project** creates a temporary project with a tox config and runs tox against it. This is the most important
  integration test fixture and uses the full flow described in Part 1.
- **demo_pkg_inline** is a minimal PEP-517 package with a custom build backend.
- **demo_pkg_setuptools** is a setuptools-based package for setuptools-specific tests.
