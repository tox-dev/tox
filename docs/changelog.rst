Release History
===============

.. include:: _draft.rst

.. towncrier release notes start

v4.0.0a5 (2021-01-23)
---------------------

Features - 4.0.0a5
~~~~~~~~~~~~~~~~~~
- Support the ``system_site_packages``/``sitepackages`` flag for virtual environment based tox environments -
  by :user:`gaborbernat`. (`#1847 <https://github.com/tox-dev/tox/issues/1847>`_)
- Support the ``always_copy``/``alwayscopy`` flag for virtual environment based tox environments -
  by :user:`gaborbernat`. (`#1848 <https://github.com/tox-dev/tox/issues/1848>`_)
- Support the ``download`` flag for virtual environment based tox environments - by :user:`gaborbernat`. (`#1849 <https://github.com/tox-dev/tox/issues/1849>`_)
- Recreate virtual environment based tox environments when the ``virtualenv`` version changes - by :user:`gaborbernat`. (`#1865 <https://github.com/tox-dev/tox/issues/1865>`_)

Bugfixes - 4.0.0a5
~~~~~~~~~~~~~~~~~~
- Not all package dependencies are installed when different tox environments in the same run use different set of
  extras - by :user:`gaborbernat`. (`#1868 <https://github.com/tox-dev/tox/issues/1868>`_)
- Support ``=`` separator in requirement file flags, directories as requirements and correctly set the root of the
  requirements file when using the ``--root`` CLI flag to change the root - by :user:`gaborbernat`. (`#1853 <https://github.com/tox-dev/tox/issues/1853>`_)
- Cleanup local subprocess file handlers when exiting runs (fixes ``ResourceWarning: unclosed file`` errors when running
  with ``env PYTHONTRACEMALLOC=5 PYTHONDEVMODE=y`` under a python built with ``--with-pydebug``)
  - by :user:`gaborbernat`. (`#1857 <https://github.com/tox-dev/tox/issues/1857>`_)
- Various small bugfixes:

  - honor updating default environment variables set by internal tox via set env (``PIP_DISABLE_PIP_VERSION_CHECK``)
  - do not multi-wrap ``HandledError`` in the ini file loader,
  - skipped environments are logged now with their fail message at default verbosity level,
  - fix an error that made the show configuration command crash when making the string of a config value failed,
  - support empty-new lines within the set env configurations replacements,

  by :user:`gaborbernat`. (`#1864 <https://github.com/tox-dev/tox/issues/1864>`_)

Improved Documentation - 4.0.0a5
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add CLI documentation - by :user:`gaborbernat`. (`#1852 <https://github.com/tox-dev/tox/issues/1852>`_)


v4.0.0a4 (2021-01-16)
---------------------

Features - 4.0.0a4
~~~~~~~~~~~~~~~~~~
- Use ``.tox/4`` instead of ``.tox4`` folder (so ignores for tox 3 works for tox 4 too), reminder we'll rename this to
  just ``.tox`` before public release, however to encourage testing tox 4 in parallel with tox 3 this is helpful
  - by :user:`gaborbernat`. (`#1812 <https://github.com/tox-dev/tox/issues/1812>`_)
- Colorize the ``config`` command: section headers are yellow, keys are green, values remained white, exceptions are light
  red and comments are cyan - by :user:`gaborbernat`. (`#1821 <https://github.com/tox-dev/tox/issues/1821>`_)

Bugfixes - 4.0.0a4
~~~~~~~~~~~~~~~~~~
- Support legacy format (``-cconstraint.txt``) of constraint files in ``deps``, and expand constraint files too when
  viewing inside the ``deps`` or calculating weather our environment is up to date or not - by :user:`gaborbernat`. (`#1788 <https://github.com/tox-dev/tox/issues/1788>`_)
- When specifying requirements/editable/constraint paths within ``deps`` escape space, unless already escaped to support
  running specifying transitive requirements files within deps - by :user:`gaborbernat`. (`#1792 <https://github.com/tox-dev/tox/issues/1792>`_)
- When using a provisioned tox environment requesting ``--recreate`` failed with ``AttributeError`` -
  by :user:`gaborbernat`. (`#1793 <https://github.com/tox-dev/tox/issues/1793>`_)
- Fix ``RequirementsFile`` from tox is rendered incorrectly in ``config`` command - by :user:`gaborbernat`. (`#1820 <https://github.com/tox-dev/tox/issues/1820>`_)
- Fix a bug in the configuration system where referring to the same named key in another env/section causes circular
  dependency error - by :user:`gaborbernat`. (`#1821 <https://github.com/tox-dev/tox/issues/1821>`_)
- Raise ``ValueError`` with descriptive message when a requirements file specified does not exist
  - by :user:`gaborbernat`. (`#1828 <https://github.com/tox-dev/tox/issues/1828>`_)
- Support all valid requirement file specification without delimiting space in the ``deps`` of the ``tox.ini`` -
  by :user:`gaborbernat`. (`#1834 <https://github.com/tox-dev/tox/issues/1834>`_)

Improved Documentation - 4.0.0a4
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add code style guide for contributors - by :user:`gaborbernat`. (`#1734 <https://github.com/tox-dev/tox/issues/1734>`_)


v4.0.0a3 (2021-01-13)
---------------------

Features - 4.0.0a3
~~~~~~~~~~~~~~~~~~
- Raise exception when set env enters into a circular reference - by :user:`gaborbernat`. (`#1779 <https://github.com/tox-dev/tox/issues/1779>`_)
- - Raise exception when variable substitution enters into a circle.
  - Add ``{/}`` as substitution for os specific path separator.
  - Add ``{env_bin_dir}`` constant substitution.
  - Implement support for ``--discover`` flag - by :user:`gaborbernat`. (`#1784 <https://github.com/tox-dev/tox/issues/1784>`_)

Bugfixes - 4.0.0a3
~~~~~~~~~~~~~~~~~~
- Entries in the ``set_env`` does not reference environments from ``set_env`` - by :user:`gaborbernat`. (`#1776 <https://github.com/tox-dev/tox/issues/1776>`_)
- ``env`` substitution does not uses values from ``set_env`` - by :user:`gaborbernat`. (`#1779 <https://github.com/tox-dev/tox/issues/1779>`_)
- Adopt tox 3 base pass env list, by adding:

  - on all platforms: ``LANG``, ``LANGUAGE``, ``CURL_CA_BUNDLE``, ``SSL_CERT_FILE`` , ``LD_LIBRARY_PATH`` and ``REQUESTS_CA_BUNLDE``,
  - on Windows: ``SYSTEMDRIVE`` - by :user:`gaborbernat`. (`#1780 <https://github.com/tox-dev/tox/issues/1780>`_)
- Fixed a bug that crashed tox where calling tox with the recreate flag and when multiple environments were reusing the
  same package - by :user:`gaborbernat`. (`#1782 <https://github.com/tox-dev/tox/issues/1782>`_)
- - Python version markers are stripped in package dependencies (after wrongfully being detected as an extra marker).
  - In packaging APIs do not set ``PYTHONPATH`` (to empty string) if ``backend-path`` is empty.
  - Fix commands parsing on Windows (do not auto-escape ``\`` - instead users should use the new ``{\}``, and on parsed
    arguments strip both ``'`` and ``"`` quoted outcomes).
  - Allow windows paths in substitution set/default (the ``:`` character used to separate substitution arguments may
    also be present in paths on Windows - do not support single capital letter values as substitution arguments) -
    by :user:`gaborbernat`. (`#1784 <https://github.com/tox-dev/tox/issues/1784>`_)
- Rework how we handle python packaging environments:

  - the base packaging environment changed from ``.package`` to ``.pkg``,
  - merged the ``sdist``, ``wheel`` and ``dev`` separate packaging implementations into one, and internally dynamically
    pick the one that's needed,
  - the base packaging environment always uses the same python environment as tox is installed into,
  - the base packaging environment is used to get the metadata of the project (via PEP-517) and to build ``sdist`` and
    ``dev`` packages,
  - for building wheels introduced a new per env configurable option ``wheel_build_env``, if the target python major/minor
    and implementation for the run tox environment and the base package tox environment matches set this to ``.pkg``,
    otherwise this is ``.pkg-{implementation}{major}{minor}``,
  - internally now packaging environments can create further packaging environments they are responsible of managing,
  - updated ``depends`` to use the packaging logic,
  - add support skip missing interpreters for depends and show config,

  by :user:`gaborbernat`. (`#1804 <https://github.com/tox-dev/tox/issues/1804>`_)


v4.0.0a2 (2021-01-09)
---------------------

Features - 4.0.0a2
~~~~~~~~~~~~~~~~~~
- Add option to disable colored output, and support ``NO_COLOR`` and ``FORCE_COLOR`` environment variables - by
  :user:`gaborbernat`. (`#1630 <https://github.com/tox-dev/tox/issues/1630>`_)

Bugfixes - 4.0.0a2
~~~~~~~~~~~~~~~~~~
- Fix coverage generation in CI - by :user:`gaborbernat`. (`#1551 <https://github.com/tox-dev/tox/issues/1551>`_)
- Fix the CI failures:

  - drop Python 3.5 support as it's not expected to get to a release before EOL,
  - fix test using ``\n`` instead of ``os.linesep``,
  - Windows Python 3.6 does not contain ``_overlapped.ReadFileInto``

  - by :user:`gaborbernat`. (`#1556 <https://github.com/tox-dev/tox/issues/1556>`_)

Improved Documentation - 4.0.0a2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add base documentation by merging virtualenv structure with tox 3 - by :user:`gaborbernat`. (`#1551 <https://github.com/tox-dev/tox/issues/1551>`_)


v4.0.0a1
--------
* First version all is brand new.

.. warning::

   The current tox is the second iteration of implementation. From version ``0.5`` all the way to ``3.X``
   we numbered the first iteration. Version ``4.0.0a1`` is a complete rewrite of the package, and as such this release
   history starts from there. The old changelog is still available in the
   `legacy branch documentation <https://tox.readthedocs.io/en/legacy/changelog.html>`_.
