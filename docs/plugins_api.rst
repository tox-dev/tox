API
===

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
