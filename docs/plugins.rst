Extending tox
=============

Extensions points
~~~~~~~~~~~~~~~~~

.. automodule:: tox.plugin
   :members:
   :exclude-members: impl

.. autodata:: tox.plugin.impl
   :no-value:

.. automodule:: tox.plugin.spec
   :members:

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

- create an issue under the ``tox-dev/tox`` Github repository with the title `Adopt plugin \<name\>
  <https://github.com/tox-dev/tox/issues/new?labels=feature%3Anew&template=feature_request.md&title=Adopt%20plugin&body=>`_,
- wait for the green light by one of our maintainers (see :ref:`current-maintainers`),
- follow the `guidance by Github
  <https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository>`_,
- (optionally) add at least one other people as co-maintainer on PyPI.

Migration from tox 3
~~~~~~~~~~~~~~~~~~~~
This section explains how the plugin interface changed between tox 3 and 4, and provides guidance for plugin developers
on how to migrate.

``tox_get_python_executable``
-----------------------------
With tox 4 the Python discovery is performed ``tox.tox_env.python.virtual_env.api._get_python`` that delegates the job
to ``virtualenv``. Therefore first `define a new virtualenv discovery mechanism
<https://virtualenv.pypa.io/en/latest/extend.html#python-discovery>`_ and then set that by setting the
``VIRTUALENV_DISCOVERY`` environment variable.

``tox_package``
---------------
Register new packager types via :func:`tox_register_tox_env <tox.plugin.spec.tox_register_tox_env>`.

``tox_addoption``
-----------------
Renamed to :func:`tox_add_option <tox.plugin.spec.tox_add_option>`.
