Plugins
=======

Many plugins are available for tox. These include, but are not limited to, the extensions found on the ``tox-dev`` org
on ':gh:`GitHub <tox-dev>`.

Plugins are automatically discovered once from the Python environment that tox itself is installed in. This means that
if tox is installed in an isolated environment (e.g. when installed using :pypi:`pipx` or :pypi:`uv`), the plugin(s)
must be installed in the same environment. To ensure a plugin is always available, you can include the plugin is listed
in :ref:`requires`, which will cause tox to auto-provision a new isolated environment with both tox and the plugin(s)
installed. For example:

.. tab:: TOML

   .. code-block:: toml

        requires = ["tox>=4", "tox-uv>=1"]

.. tab:: INI

   .. code-block:: ini

        [tox]
        requires =
            tox>=4
            tox-uv>=1

For more information, refer to :ref:`the user guide <auto-provisioning>`.

Plugins can be disabled via the ``TOX_DISABLED_EXTERNAL_PLUGINS`` environment variable. This variable can be set to a
comma separated list of plugin names, e.g.:

```bash
env TOX_DISABLED_EXTERNAL_PLUGINS=tox-uv,tox-extra tox --version
```

Developing your own plugin
--------------------------

The below provides some guidance on how to develop your own plugin for tox. A reference guide to the plugin API can be
found in :doc:`plugins_api`.

Extensions points
~~~~~~~~~~~~~~~~~

.. automodule:: tox.plugin
   :members:
   :exclude-members: impl

.. autodata:: tox.plugin.impl
   :no-value:

.. automodule:: tox.plugin.spec
   :members:

A plugin can define its plugin module a:

.. code-block:: python

   def tox_append_version_info() -> str:
       return "magic"

and this message will be appended to the output of the ``--version`` flag.

Adoption of a plugin under tox-dev Github organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You're free to host your plugin on your favorite platform, however the core tox development is happening on Github,
under the ``tox-dev`` org organization. We are happy to adopt tox plugins under the ``tox-dev`` organization if:

- we determine it's trying to solve a valid use case and it's not malicious (e.g. no plugin that deletes the users home
  directory),
- it's released on PyPI with at least 100 downloads per month (to ensure it's a plugin used by people).

What's in for you in this:

- you get owner rights on the repository under the tox-dev organization,
- exposure of your plugin under the core umbrella,
- backup maintainers from other tox plugin development.

How to apply:

- create an issue under the ``tox-dev/tox`` Github repository with the title
  :gh:`Adopt plugin \<name\> <login?return_to=https%3A%2F%2Fgithub.com%2Ftox-dev%2Ftox%2Fissues%2Fnew%3Flabels%3Dfeature%253Anew%26template%3Dfeature_request.md%26title%3DAdopt%2520plugin%26body%3D>`,
- wait for the green light by one of our maintainers (see :ref:`current-maintainers`),
- follow the `guidance by Github
  <https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository>`_,
- (optionally) add at least one other people as co-maintainer on PyPI.

Migration from tox 3
~~~~~~~~~~~~~~~~~~~~

This section explains how the plugin interface changed between tox 3 and 4, and provides guidance for plugin developers
on how to migrate.

``tox_get_python_executable``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With tox 4 the Python discovery is performed ``tox.tox_env.python.virtual_env.api._get_python`` that delegates the job
to ``virtualenv``. Therefore first `define a new virtualenv discovery mechanism
<https://virtualenv.pypa.io/en/latest/extend.html#python-discovery>`_ and then set that by setting the
``VIRTUALENV_DISCOVERY`` environment variable.

``tox_package``
^^^^^^^^^^^^^^^

Register new packager types via :func:`tox_register_tox_env <tox.plugin.spec.tox_register_tox_env>`.

``tox_addoption``
^^^^^^^^^^^^^^^^^

Renamed to :func:`tox_add_option <tox.plugin.spec.tox_add_option>`.
