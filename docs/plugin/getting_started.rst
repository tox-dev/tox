###################
 Your first plugin
###################

You can define plugins directly in your project by creating a ``toxfile.py`` file next to your tox configuration file.
This avoids the need to package and install a separate plugin. All the same hooks are available.

**************************************
 Your first plugin: adding a CLI flag
**************************************

Create a ``toxfile.py`` that adds a ``--magic`` flag to the tox CLI:

.. code-block:: python

    from tox.config.cli.parser import ToxParser
    from tox.plugin import impl


    @impl
    def tox_add_option(parser: ToxParser) -> None:
        parser.add_argument("--magic", action="store_true", help="enable magic mode")

Place this file next to your ``tox.toml`` or ``tox.ini``. When tox starts, it discovers and loads ``toxfile.py``
automatically.

************************
 Appending version info
************************

A ``toxfile.py`` that appends text to the ``tox --version`` output:

.. code-block:: python

    from tox.plugin import impl


    @impl
    def tox_append_version_info() -> str:
        return "magic"

************************
 Providing environments
************************

Plugins can dynamically inject tox environments that don't need to be declared in ``tox.toml`` or ``tox.ini``. This uses
two hooks together: :func:`tox_extend_envs <tox.plugin.spec.tox_extend_envs>` to declare the environment name, and
:func:`tox_add_core_config <tox.plugin.spec.tox_add_core_config>` with :class:`~tox.config.loader.memory.MemoryLoader`
to configure it.

For example, a ``toxfile.py`` that adds a ``lint`` environment running `pre-commit <https://pre-commit.com>`_:

.. code-block:: python

    from collections.abc import Iterable

    from tox.config.loader.memory import MemoryLoader
    from tox.config.sets import ConfigSet
    from tox.plugin import impl
    from tox.session.state import State


    @impl
    def tox_extend_envs() -> Iterable[str]:
        return ("lint",)


    @impl
    def tox_add_core_config(core_conf: ConfigSet, state: State) -> None:
        state.conf.memory_seed_loaders["lint"].append(
            MemoryLoader(
                description="run pre-commit linters",
                commands=[["pre-commit", "run", "--all-files"]],
                deps=["pre-commit"],
            ),
        )

With this ``toxfile.py`` in your project root, ``tox list`` shows the ``lint`` environment and ``tox run -e lint``
executes it -- no configuration file entry needed.

Any :ref:`configuration key <conf-testenv>` accepted by the environment can be passed as a keyword argument to
``MemoryLoader``. Values from ``MemoryLoader`` act as defaults and can still be overridden by the configuration file or
CLI ``--override``.
