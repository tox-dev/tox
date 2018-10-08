3.5.0 (2018-10-08)
------------------

Bugfixes
^^^^^^^^

- intermittent failures with ``--parallel--safe-build``, instead of mangling with the file paths now uses a lock to make the package build operation thread safe and is now on by default (``--parallel--safe-build`` is now deprecated) - by :user:`gaborbernat` (`#1026 <https://github.com/tox-dev/tox/issues/1026>`_)


Features
^^^^^^^^

- Added ``temp_dir`` folder configuration (defaults to ``{toxworkdir}/.tmp``) that contains tox
  temporary files. Package builds now create a hard link (if possible, otherwise copy - notably in
  case of Windows Python 2.7) to the built file, and feed that file downstream (e.g. for pip to
  install it). The hard link is removed at the end of the run (what it points though is kept
  inside ``distdir``). This ensures that a tox session operates on the same package it built, even
  if a parallel tox run builds another version. Note ``distdir`` will contain only the last built
  package in such cases. - by :user:`gaborbernat` (`#1026 <https://github.com/tox-dev/tox/issues/1026>`_)


Documentation
^^^^^^^^^^^^^

- document tox environment recreate rules (:ref:`recreate`) - by :user:`gaborbernat` (`#93 <https://github.com/tox-dev/tox/issues/93>`_)
- document inside the ``--help`` how to disable colorized output via the ``PY_COLORS`` operating system environment variable - by :user:`gaborbernat` (`#163 <https://github.com/tox-dev/tox/issues/163>`_)
- document all global tox flags and a more concise format to express default and type - by :user:`gaborbernat` (`#683 <https://github.com/tox-dev/tox/issues/683>`_)
- document command line interface under the config section `cli <https://tox.readthedocs.io/en/latest/config.html?highlight=cli#cli>`_ - by :user:`gaborbernat` (`#829 <https://github.com/tox-dev/tox/issues/829>`_)
