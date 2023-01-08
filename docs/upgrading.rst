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

- On Windows, the tty trait of the caller environment is no longer passed through. The most notable impact of this
  change is that some tools no longer show colored output. You may need to force colorization to be for such enabled
  for such tools. See :issue:`2337` for more details.

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

Failure when all environments are skipped
-----------------------------------------

A run that results in all environments being skipped will no longer result in success. Instead, a failure will be
reported. For example, consider a host that does not support Python 3.5:

.. code-block:: bash

   tox run --skip-missing-interpreters=true -e py35

This will now result in a failure.

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

CLI command compatibility
-------------------------

``tox`` 4 introduced dedicated subcommands for various usages.
However, when no subcommand is given the legacy entry point which imitates ``tox`` 3 is used.

This compatibility feature makes most ``tox`` 3 commands work in ``tox`` 4, but there are some exceptions.

Updating usage with ``-e``
++++++++++++++++++++++++++

In ``tox`` 3, environments could be specified to run with the ``-e`` flag.
In ``tox`` 4, environments should always be specified using the ``-e`` flag to the ``run`` subcommand.

Rewrite usages as follows

.. code:: bash

    # tox 3
    tox -e py310,style

    # tox 4
    tox run -e py310,style

    # or, tox 4 with the short alias
    tox r -e py310,style

Environment names matching commands
+++++++++++++++++++++++++++++++++++

Now that ``tox`` has subcommands, it is possible for arguments to ``tox`` or its options to match those subcommand
names.
When that happens, parsing can become ambiguous between the ``tox`` 4 usage and the legacy fallback behavior.

For example, consider the following tox config:

.. code-block:: ini

    [tox]
    env_list = py39,py310

    [testenv]
    commands =
        python -c 'print("hi")'

    [testenv:list]
    commands =
        python -c 'print("a, b, c")'

This defines an environment whose name matches a ``tox`` 4 command, ``list``.

Under ``tox`` 3, ``tox -e list`` specified the ``list`` environment.
However, under ``tox`` 4, the parse of this usage as an invocation of ``tox list`` takes precedence over the legacy
behavior.

Therefore, attempting that same usage results in an error:

.. code:: bash

    $ tox -e list
    ...
    tox: error: unrecognized arguments: -e

This is best avoided by updating to non-legacy usage:

.. code:: bash

    $ tox run -e list

    # or, equivalently...
    $ tox r -e list

Packaging environments
----------------------

Isolated environment on by default
++++++++++++++++++++++++++++++++++
``tox`` now always uses an isolated build environment when building your projects package. The previous flag to enable
this called ``isolated_build`` has been removed.

Packaging configuration and inheritance
+++++++++++++++++++++++++++++++++++++++
Isolated build environments are tox environments themselves and may be configured on their own. Their name is defined
as follows:

- For source distributions this environment will match a virtual environment with the same python interpreter as tox is
  using. The name of this environment will by default ``.pkg`` (can be changed via :ref:`package_env` config on a per
  test environment basis).
- For wheels (including editable wheels as defined by :pep:`660`) their name will be ``.pkg-<impl><python_version>``, so
  for example if you're building a wheel for a Python 3.10 environment the packaging environment will be
  ``.pkg-cpython311``  (can be changed via :ref:`wheel_build_env` config on a per test environment basis).

To change a packaging environments settings you can use:

.. code-block:: ini

    [testenv:.pkg]
    pass_env =
        PKG_CONFIG
        PKG_CONFIG_PATH
        PKG_CONFIG_SYSROOT_DIR

    [testenv:.pkg-cpython311]
    pass_env =
        PKG_CONFIG
        PKG_CONFIG_PATH
        PKG_CONFIG_SYSROOT_DIR

Packaging environments no longer inherit their settings from the ``testenv`` section, as this caused issues when
some test environment settings conflicted with packaging setting. However starting with ``tox>=4.2`` all packaging
environments inherit from the ``pkgenv`` section, allowing you to define packaging common packaging settings in one
central place, while still allowing you to override it when needed on a per package environment basis:

.. code-block:: ini

    [pkgenv]
    pass_env =
        PKG_CONFIG
        PKG_CONFIG_PATH
        PKG_CONFIG_SYSROOT_DIR

    [testenv:.pkg-cpython311]
    pass_env =
        {[pkgenv]pass_env}
        IS_311 = yes

    [testenv:magic]
    package = sdist
    pass_env = {[pkgenv]pass_env}  # sdist install builds wheel -> need packaging settings

Note that specific packaging environments are defined under ``testenv:.pkg`` and **not** ``pkgenv:.pkg``, this is due
backwards compatibility.

Universal wheels
++++++++++++++++
If your project builds universal wheels you can avoid using multiple build environments for each targeted python by
setting :ref:`wheel_build_env` to the same packaging environment via:

.. code-block:: ini

    [testenv]
    package = wheel
    wheel_build_env = .pkg

Editable mode
+++++++++++++
``tox`` now defaults to using editable wheels when develop mode is enabled and the build backend supports it,
as defined by :pep:`660` by setting :ref:`package` to ``editable``. In case the backend does not support it, will
fallback to :ref:`package` to ``editable-legacy``, and invoke pip with ``-e``. In the later case will also print a
message to make this setting explicit in your configuration (explicit better than implicit):

.. code-block:: ini

    [testenv:dev]
    package = editable-legacy

If you want to use the new standardized method to achieve the editable install effect you should ensure your backend
version is above the version this feature was added to it, for example for setuptools:

.. code-block:: ini

    [testenv:dev]
    deps = setuptools>=64
    package = editable
