Plugin system
=============

Plugin API
~~~~~~~~~~
.. automodule:: tox.plugin
   :members:
   :exclude-members: impl

.. autodata:: tox.plugin.impl
   :no-value:

.. automodule:: tox.plugin.spec
   :members:

tox objects
~~~~~~~~~~~

register
--------

.. automodule:: tox.tox_env.register
   :members:
   :exclude-members: REGISTER

.. autodata:: REGISTER
   :no-value:

config
------
.. autoclass:: tox.config.cli.parser.Parsed
   :members:

.. autoclass:: tox.config.main.Config
   :members:
   :exclude-members: __init__, make

.. autoclass:: tox.config.sets.ConfigSet
   :members:
   :special-members: __iter__, __contains__

.. autoclass:: tox.config.sets.CoreConfigSet
   :members:

.. autoclass:: tox.config.sets.EnvConfigSet
   :members:

.. autoclass:: tox.config.of_type.ConfigDefinition
   :members:

.. autoclass:: tox.config.of_type.ConfigDynamicDefinition
   :members:

.. autoclass:: tox.config.of_type.ConfigConstantDefinition
   :members:

.. autoclass:: tox.config.source.api.Source
   :members:

.. autoclass:: tox.config.loader.api.Override
   :members:

.. autoclass:: tox.config.loader.api.Loader
   :members:

.. autoclass:: tox.config.loader.convert.Convert
   :members:

.. autoclass:: tox.config.types.EnvList
   :members:
   :special-members: __bool__, __iter__

.. autoclass:: tox.config.types.Command
   :members:

environments
------------
.. autoclass:: tox.tox_env.api.ToxEnv
   :members:

.. autoclass:: tox.tox_env.runner.RunToxEnv
   :members:

.. autoclass:: tox.tox_env.package.PackageToxEnv
   :members:

.. autoclass:: tox.tox_env.package.Package
   :members:

journal
-------
.. autoclass:: tox.journal.env.EnvJournal
   :members:
   :exclude-members: __init__
   :special-members: __bool__, __setitem__

report
------
.. autoclass:: tox.report.ToxHandler
   :members:
   :exclude-members: stream, format, patch_thread, write_out_err, suspend_out_err

execute
-------
.. autoclass:: tox.execute.request.ExecuteRequest
   :members:

.. autoclass:: tox.execute.request.StdinSource
   :members:

.. autoclass:: tox.execute.api.Outcome
   :members:

.. autoclass:: tox.execute.api.Execute
   :members:

.. autoclass:: tox.execute.api.ExecuteStatus
   :members:

.. autoclass:: tox.execute.api.ExecuteInstance
   :members:

.. autoclass:: tox.execute.stream.SyncWrite
   :members:

installer
---------

.. autoclass:: tox.tox_env.installer.Installer
   :members:

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

``tox_adoption``
----------------
Renamed to :func:`tox_add_option <tox.plugin.spec.tox_add_option>`.
