tox can now run commands from an environment, and find the package built by a ``package = external`` environment, when
the :ref:`work_dir` or :ref:`tox_root` path contains a ``[``, ``*`` or ``?``. Before, those characters were read as glob
syntax, so the environment's own ``python`` was reported as not allowed and the default or relative
:ref:`package_glob` matched nothing.
