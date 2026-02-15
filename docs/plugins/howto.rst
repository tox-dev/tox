######################
 Plugin How-to Guides
######################

***********************
 Plugin hook lifecycle
***********************

The diagram below shows when each plugin hook fires during a tox run:

.. mermaid::

    flowchart TD
        start(( )) --> register[tox_register_tox_env]
        register --> add_option[tox_add_option]
        add_option --> extend[tox_extend_envs]
        extend --> core_config[tox_add_core_config]
        core_config --> env_config[tox_add_env_config]

        env_config --> envloop

        subgraph envloop [for each environment]
            direction TB
            on_install[tox_on_install]
            on_install --> before[tox_before_run_commands]
            before --> cmds[run commands]
            cmds --> after[tox_after_run_commands]
            after --> teardown[tox_env_teardown]
        end

        teardown --> done(( ))

        classDef setupStyle fill:#dbeafe,stroke:#3b82f6,stroke-width:2px,color:#1e3a5f
        classDef envStyle fill:#dcfce7,stroke:#22c55e,stroke-width:2px,color:#14532d
        classDef cmdStyle fill:#ede9fe,stroke:#8b5cf6,stroke-width:2px,color:#3b0764
        classDef installStyle fill:#ffedd5,stroke:#f97316,stroke-width:2px,color:#7c2d12

        class register,add_option,extend,core_config,env_config setupStyle
        class before,after,teardown envStyle
        class cmds cmdStyle
        class on_install installStyle

*************************************
 Add custom config to an environment
*************************************

Use :func:`tox_add_env_config <tox.plugin.spec.tox_add_env_config>` to register new configuration keys on every tox
environment. Users can then set these keys in ``tox.toml`` or ``tox.ini`` like any built-in setting.

.. code-block:: python

    from tox.config.sets import EnvConfigSet
    from tox.plugin import impl
    from tox.session.state import State


    @impl
    def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:
        env_conf.add_config(
            keys=["my_timeout"],
            of_type=int,
            default=30,
            desc="timeout in seconds for custom checks",
        )

Access the value later via ``env_conf["my_timeout"]``.

***********************************
 Run code before or after commands
***********************************

Use :func:`tox_before_run_commands <tox.plugin.spec.tox_before_run_commands>` and :func:`tox_after_run_commands
<tox.plugin.spec.tox_after_run_commands>` to execute logic around the ``commands`` phase. The ``tox_after_run_commands``
hook receives the exit code and the list of :class:`~tox.execute.api.Outcome` objects for each command.

.. code-block:: python

    import time

    from tox.execute import Outcome
    from tox.plugin import impl
    from tox.tox_env.api import ToxEnv

    _start: float = 0


    @impl
    def tox_before_run_commands(tox_env: ToxEnv) -> None:
        global _start  # noqa: PLW0603
        _start = time.monotonic()


    @impl
    def tox_after_run_commands(
        tox_env: ToxEnv, exit_code: int, outcomes: list[Outcome]
    ) -> None:
        elapsed = time.monotonic() - _start
        tox_env.conf.core["report"].verbosity0(
            f"{tox_env.conf['env_name']} finished in {elapsed:.1f}s "
            f"(exit code {exit_code})",
        )

*********************************
 Intercept package installations
*********************************

Use :func:`tox_on_install <tox.plugin.spec.tox_on_install>` to run logic whenever tox installs packages (deps, the
project itself, etc.). The ``section`` and ``of_type`` parameters identify which install phase triggered the call.

.. code-block:: python

    from typing import Any

    from tox.plugin import impl
    from tox.tox_env.api import ToxEnv


    @impl
    def tox_on_install(tox_env: ToxEnv, arguments: Any, section: str, of_type: str) -> None:
        print(f"Installing [{section}] {of_type}: {arguments}")  # noqa: T201

*******************************
 Clean up after an environment
*******************************

Use :func:`tox_env_teardown <tox.plugin.spec.tox_env_teardown>` to run cleanup logic after an environment finishes,
regardless of whether commands succeeded or failed.

.. code-block:: python

    from tox.plugin import impl
    from tox.tox_env.api import ToxEnv


    @impl
    def tox_env_teardown(tox_env: ToxEnv) -> None:
        cache_dir = tox_env.env_dir / ".cache"
        if cache_dir.exists():
            import shutil

            shutil.rmtree(cache_dir)

**************************************
 Register a custom environment runner
**************************************

Use :func:`tox_register_tox_env <tox.plugin.spec.tox_register_tox_env>` to register a custom run or package environment
type. This is the hook used by plugins like ``tox-uv`` to replace the default virtualenv-based runner.

.. code-block:: python

    from tox.plugin import impl
    from tox.tox_env.python.virtual_env.runner import VirtualEnvRunner
    from tox.tox_env.register import ToxEnvRegister


    class MyRunner(VirtualEnvRunner):
        @staticmethod
        def id() -> str:
            return "my-runner"

        # override methods to customize behavior


    @impl
    def tox_register_tox_env(register: ToxEnvRegister) -> None:
        register.add_run_env(MyRunner)

Set ``runner = my-runner`` in a tox environment to use it.

***********************************
 Package a plugin for distribution
***********************************

While ``toxfile.py`` works for project-local plugins, distributable plugins are standard Python packages that declare
the ``tox`` entry point.

In ``pyproject.toml``:

.. code-block:: toml

    [project]
    name = "tox-myplugin"
    version = "1.0.0"
    dependencies = ["tox>=4"]

    [project.entry-points.tox]
    myplugin = "tox_myplugin"

In ``src/tox_myplugin/__init__.py``, define your hooks exactly as in ``toxfile.py``:

.. code-block:: python

    from tox.plugin import impl


    @impl
    def tox_append_version_info() -> str:
        return "myplugin-1.0.0"

After ``pip install tox-myplugin``, tox discovers the plugin automatically via the entry point.

******************
 Extension points
******************

.. automodule:: tox.plugin
    :members:
    :exclude-members: impl

.. autodata:: tox.plugin.impl
    :no-value:

.. automodule:: tox.plugin.spec
    :members:

**************************************************
 Adopting a plugin under the tox-dev organization
**************************************************

You're free to host your plugin on your favorite platform. However, the core tox development happens on GitHub under the
``tox-dev`` organization. We are happy to adopt tox plugins under the ``tox-dev`` organization if:

- the plugin solves a valid use case and is not malicious,
- it's released on PyPI with at least 100 downloads per month (to ensure it's actively used).

What's in it for you:

- you get owner rights on the repository under the tox-dev organization,
- exposure of your plugin under the core umbrella,
- backup maintainers from other tox plugin developers.

How to apply:

- create an issue under the ``tox-dev/tox`` GitHub repository with the title :gh:`Adopt plugin \<name\>
  <login?return_to=https%3A%2F%2Fgithub.com%2Ftox-dev%2Ftox%2Fissues%2Fnew%3Flabels%3Dfeature%253Anew%26template%3Dfeature_request.md%26title%3DAdopt%2520plugin%26body%3D>`,
- wait for the green light by one of the maintainers (see :ref:`current-maintainers`),
- follow the `guidance by GitHub
  <https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository>`_,
- (optionally) add at least one other person as co-maintainer on PyPI.
