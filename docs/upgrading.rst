.. _upgrading:

Upgrading to tox v4
===================

Version 4 is mostly backwards compatible.
This document covers all breaking changes and, where applicable, includes guidance on how to update.

See also the list of new features in the :ref:`FAQ <faq>`.

Python support
--------------

- tox now requires Python ``3.7`` or later and is tested only against CPython. You can still create test environments
  for earlier Python versions or different Python interpreters. PyPy support is best effort, meaning we do not test it
  as part of our CI runs, however if you discover issues under PyPy we will accept PRs addressing it.

Changed INI rules
-----------------

- The hash sign (``#``) now always acts as comment within ``tox.ini`` or ``setup.cfg`` tox configuration file. Where you
  need to pass on a ``#`` character you will need to escape it in form of ``\#`` so tox does not handle everything right
  of the ``#`` character as a comment. Valid in tox 3:

  .. code-block:: ini

      # valid in tox 3
      commands = bash -c "echo 'foo#bar'"

      # valid in tox 4
      commands = bash -c "echo 'foo\#bar'"

- Within the ``pass_env`` you can no longer use space as value separator, instead you need to use the ``,`` or the
  newline character. This is to have the same value separation rules for all tox configuration lines.

  .. code-block:: ini

      # valid in tox 3
      passenv = ALPHA BETA
      passenv =
          ALPHA
          BETA

      # valid in tox 4
      passenv = ALPHA, BETA
      passenv =
          ALPHA
          BETA

- tox 4 now errors when using the ``-U`` flag when defining dependencies, e.g. ``deps = -Ur requirements.txt``. While
  this worked in tox 3, it was never supported officially. Additionally, in the context of a new virtual environment
  this flag makes no sense anyway.

- tox 4 requires the ``install_command`` to evaluate to a non-empty value for each target environment.  In tox 3, an
  empty value would be substituted for the default install command.

Known regressions
-----------------

- With tox 4 the tty trait of the caller environment is no longer passed through. The most notable impact of this is
  that some tools no longer print colored output. A PR to address this is welcomed, in the meantime you can use the
  ``tty`` substitution to force color mode for these tools, see for example tox itself with pytest and mypy
  `here in tox.ini <https://github.com/tox-dev/tox/blob/main/tox.ini#L28>`_.

New plugin system
-----------------

tox 4 is a grounds up rewrite of the code base, and while we kept the configuration layer compatibility no such effort
has been made for the programmatic API. Therefore, all plugins will need to redo their integration against the new code
base. If you're a plugin developer refer to the `plugin documentation <https://tox.wiki/en/latest/plugins.html>`_ for
more information.

Removed tox.ini keys
--------------------

+--------------------------+-----------------------------------------------------------------+
| Configuration key        | Migration path                                                  |
+==========================+=================================================================+
| ``indexserver``          | See :ref:`Using a custom PyPI server <faq_custom_pypi_server>`. |
+--------------------------+-----------------------------------------------------------------+
| ``whitelist_externals``  | Use :ref:`allowlist_externals` key instead.                     |
+--------------------------+-----------------------------------------------------------------+
| ``isolated_build``       | Isolated builds are now always used.                            |
+--------------------------+-----------------------------------------------------------------+
| ``distdir``              | Use the ``TOX_PACKAGE`` environment variable.                   |
+--------------------------+-----------------------------------------------------------------+

basepython not resolved
-----------------------

The base python configuration is no longer resolved to ``pythonx.y`` format, instead is kept as ``py39``, and is
the virtualenv project that handles mapping that to a Python interpreter. If you were using this variable we recommend
moving to the newly added ``py_impl`` and ``py_dot_ver`` variables, for example:

.. code-block:: ini

   deps = -r{py_impl}{py_dot_ver}-req.txt

Substitutions removed
---------------------

- The ``distshare`` substitution has been removed.

Disallowed env names
--------------------

- Environment names that contain multiple Python variants, such as ``name-py39-pypy`` or ``py39-py310`` will now raise
  an error, previously this only warned, you can use :ref:`ignore_basepython_conflict` to disable this error, but we
  recommend changing the name to avoid this name that can be confusing.

CLI arguments changed
---------------------

- The ``--parallel--safe-build`` CLI argument has been removed, no longer needed.
- When you want to pass an option to a test command, e.g. to ``pytest``, now you must use ``--`` as a separator, this
  worked with version 3 also, but any unknown trailing arguments were automatically passed through, while now this is
  no longer the case.
- Running ``--showconfig`` or ``--help-ini`` with the ``-v`` flag will add interleaved debugging information, whereas
  tox 3 added additional lines at the start. If you want to generate valid ini files you must not use the ``-v`` flag.
- The ``--index-url`` is now removed, use ``PIP_INDEX_URL`` in :ref:`set_env` instead.

Packaging changes
-----------------

- We use isolated builds (always) as specified by :pep:`518` and use :pep:`517` to communicate with the build backend.
- The ``--develop`` CLI flag or the :ref:`use_develop` settings now enables editable installations via the :pep:`660`
  mechanism rather than the legacy ``pip install -e`` behaviour. The old functionality can still be forced by setting
  the :ref:`package` setting for the run environment to ``editable-legacy``.

Output changes
--------------

- We now use colors for reporting, to help make the output easier to read for humans. This can be disabled via the
  ``TERM=dumb`` or ``NO_COLOR=1`` environment variables, or the ``--colored no`` CLI argument.

Re-use of environments
----------------------

- It is no longer possible to re-use environments. While this might have been possible with tox version 3, this
  behavior was never supported, and possibly caused wrong results as illustrated in the following example.

.. code-block:: ini

    [testenv]
    envdir = .tox/venv

    [testenv:a]
    deps = pytest>7

    [testenv:b]
    deps = pytest<7
