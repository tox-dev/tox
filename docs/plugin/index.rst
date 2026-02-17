#########
 Plugins
#########

Many plugins are available for tox. These include, but are not limited to, the extensions found on the ``tox-dev`` org
on :gh:`GitHub <tox-dev>`.

*****************
 Popular plugins
*****************

- :pypi:`tox-uv` - Use :pypi:`uv` for faster package installation.
- :pypi:`tox-gh-actions` - Integrate tox with GitHub Actions for efficient CI workflows.
- :pypi:`tox-gh` - Enhanced GitHub integration for running tox across multiple environments.
- :pypi:`tox-extra` - Add sanity checks before/after tests (dirty repo detection, system dependencies).
- :pypi:`tox-recreate` - Automatically recreate environments when dependency files change.
- :pypi:`tox-multipython` - Interpreter discovery for multipython.

Plugins are automatically discovered from the Python environment that tox itself is installed in. This means that if tox
is installed in an isolated environment (e.g. when installed using :pypi:`pipx` or :pypi:`uv`), the plugin(s) must be
installed in the same environment. To ensure a plugin is always available, include it in :ref:`requires`, which causes
tox to :ref:`auto-provision <auto-provisioning>` a new isolated environment with both tox and the plugin(s) installed.
For example:

.. tab:: TOML

    .. code-block:: toml

         requires = ["tox>=4", "tox-uv>=1"]

.. tab:: INI

    .. code-block:: ini

         [tox]
         requires =
             tox>=4
             tox-uv>=1

*******************
 Disabling plugins
*******************

Plugins can be disabled via the ``TOX_DISABLED_EXTERNAL_PLUGINS`` environment variable. Set it to a comma-separated list
of plugin names:

.. code-block:: bash

    env TOX_DISABLED_EXTERNAL_PLUGINS=tox-uv,tox-extra tox --version

.. toctree::
    :hidden:

    getting_started
    howto
    api
