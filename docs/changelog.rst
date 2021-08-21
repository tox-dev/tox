Release History
===============
.. include:: _draft.rst

.. towncrier release notes start

v4.0.0a8 (2021-08-21)
---------------------

Features - 4.0.0a8
~~~~~~~~~~~~~~~~~~
- Add support for :ref:`allowlist_externals`, commands not matching error - by :user:`gaborbernat`. (`#1127 <https://github.com/tox-dev/tox/issues/1127>`_)
- Add outcome of environments into the result json (:ref:`--result-json <tox-run---result-json>`) under the ``result`` key
  containing ``success`` boolean, ``exit_code`` integer and ``duration`` float value  - by :user:`gaborbernat`. (`#1405 <https://github.com/tox-dev/tox/issues/1405>`_)
- Add ``exec`` subcommand that allows users to run an arbitrary command within the tox environment (without needing to
  modify their configuration) - by :user:`gaborbernat`. (`#1790 <https://github.com/tox-dev/tox/issues/1790>`_)
- Add check to validate the base Python names and the environments name do not conflict Python spec wise, when they do
  raise error if :ref:`ignore_base_python_conflict` is not set or ``False`` - by :user:`gaborbernat`. (`#1840 <https://github.com/tox-dev/tox/issues/1840>`_)
- Allow any Unix shell-style wildcards expression for  :ref:`pass_env` - by :user:`gaborbernat`. (`#2121 <https://github.com/tox-dev/tox/issues/2121>`_)
- Add support for :ref:`args_are_paths` flag - by :user:`gaborbernat`. (`#2122 <https://github.com/tox-dev/tox/issues/2122>`_)
- Add support for :ref:`env_log_dir` (compared to tox 3 extend content and keep only last run entries) -
  by :user:`gaborbernat`. (`#2123 <https://github.com/tox-dev/tox/issues/2123>`_)
- Add support for ``{:}`` substitution in ini files as placeholder for the OS path separator - by :user:`gaborbernat`. (`#2125 <https://github.com/tox-dev/tox/issues/2125>`_)
- When cleaning directories (for tox environment, ``env_log_dir``, ``env_tmp_dir`` and packaging metadata folders) do not
  delete the directory itself and recreate, but instead just delete its content (this allows the user to cd into it and
  still be in a valid folder after a new run) - by :user:`gaborbernat`. (`#2139 <https://github.com/tox-dev/tox/issues/2139>`_)
- Changes to help plugin development: simpler tox env creation argument list, expose python creation directly,
  allow skipping list dependencies install command for pip and executable is only part of the python cache for virtualenv
  - by :user:`gaborbernat`. (`#2172 <https://github.com/tox-dev/tox/issues/2172>`_)

Bugfixes - 4.0.0a8
~~~~~~~~~~~~~~~~~~
- Support ``#`` character in path for the tox project - by :user:`gaborbernat`. (`#763 <https://github.com/tox-dev/tox/issues/763>`_)
- If the command expression fails to parse with shlex fallback to literal pass through of the remaining elements
  - by :user:`gaborbernat`. (`#1944 <https://github.com/tox-dev/tox/issues/1944>`_)
- tox config fails on `--recreate <tox-config---recreate>`_ flag, and once specified the output does not reflect the
  impact of the CLI flags - by :user:`gaborbernat`. (`#2037 <https://github.com/tox-dev/tox/issues/2037>`_)
- Virtual environment creation for Python is always triggered at every run - by :user:`gaborbernat`. (`#2041 <https://github.com/tox-dev/tox/issues/2041>`_)
- Add support for setting :ref:`suicide_timeout`, :ref:`interrupt_timeout` and :ref:`terminate_timeout` - by
  :user:`gaborbernat`. (`#2124 <https://github.com/tox-dev/tox/issues/2124>`_)
- Parallel show output not working when there's a packaging phase in the run - by :user:`gaborbernat`. (`#2161 <https://github.com/tox-dev/tox/issues/2161>`_)

Improved Documentation - 4.0.0a8
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Note constraint files are a subset of requirement files - by :user:`gaborbernat`. (`#1939 <https://github.com/tox-dev/tox/issues/1939>`_)
- Add a note about having a package with different Python requirements than tox and not specifying :ref:`base_python` -
  by :user:`gaborbernat`. (`#1975 <https://github.com/tox-dev/tox/issues/1975>`_)
- Fix :ref:`--runner <tox---runner>` is missing default value and documentation unclear - by :user:`gaborbernat`. (`#2004 <https://github.com/tox-dev/tox/issues/2004>`_)


v4.0.0a7 (2021-07-28)
---------------------

Features - 4.0.0a7
~~~~~~~~~~~~~~~~~~
- Add support for configuration taken from the ``setup.cfg`` file -by :user:`gaborbernat`. (`#1836 <https://github.com/tox-dev/tox/issues/1836>`_)
- Add support for configuration taken from the ``pyproject.toml`` file, ``tox`` section ``legacy_tox_ini`` key - by
  :user:`gaborbernat`. (`#1837 <https://github.com/tox-dev/tox/issues/1837>`_)
- Add configuration documentation - by :user:`gaborbernat`. (`#1914 <https://github.com/tox-dev/tox/issues/1914>`_)
- Implemented ``[]`` substitution (alias for ``{posargs}``) - by
  :user:`hexagonrecursion`. (`#1928 <https://github.com/tox-dev/tox/issues/1928>`_)
- Implement ``[testenv] ignore_outcome`` - "a failing result of this testenv will not make tox fail" - by :user:`hexagonrecursion`. (`#1947 <https://github.com/tox-dev/tox/issues/1947>`_)
- Inline plugin support via ``tox_.py``. This is loaded where the tox config source is discovered. It's a Python file
  that can contain arbitrary Python code, such as definition of a plugin. Eventually we'll add a plugin that allows
  succinct declaration/generation of new tox environments - by :user:`gaborbernat`. (`#1963 <https://github.com/tox-dev/tox/issues/1963>`_)
- Introduce the installer concept, and collect pip installation into a ``pip`` package, also attach to this
  the requirements file parsing which got a major rework - by :user:`gaborbernat`. (`#1991 <https://github.com/tox-dev/tox/issues/1991>`_)
- Support CPython ``3.10`` -by :user:`gaborbernat`. (`#2014 <https://github.com/tox-dev/tox/issues/2014>`_)

Bugfixes - 4.0.0a7
~~~~~~~~~~~~~~~~~~
- Environments with a platform mismatch are no longer silently skipped, but properly reported - by :user:`jugmac00`. (`#1926 <https://github.com/tox-dev/tox/issues/1926>`_)
- Port pip requirements file parser to ``tox`` to achieve full equivalency (such as support for the per requirement
  ``--install-option`` and ``--global-option`` flags) - by :user:`gaborbernat`. (`#1929 <https://github.com/tox-dev/tox/issues/1929>`_)
- Support for extras with paths for Python deps and requirement files - by :user:`gaborbernat`. (`#1933 <https://github.com/tox-dev/tox/issues/1933>`_)
- Due to a bug ``\{posargs} {posargs}`` used to expand to literal ``{posargs} {posargs}``.
  Now the second ``{posargs}`` is expanded.
  ``\{posargs} {posargs}`` expands to ``{posargs} positional arguments here`` - by :user:`hexagonrecursion`. (`#1956 <https://github.com/tox-dev/tox/issues/1956>`_)
- Enable setting a different ``upstream`` repository for the coverage diff report.
  This has been hardcoded to ``upstream/rewrite`` until now.
  by :user:`jugmac00`. (`#1972 <https://github.com/tox-dev/tox/issues/1972>`_)
- Enable replacements (a.k.a section substitions) for section names containing a dash in sections
  without the ``testenv:`` prefix - by :user:`jugmac00`, :user:`obestwalter`, :user:`eumiro`. (`#1985 <https://github.com/tox-dev/tox/issues/1985>`_)
- Fix legacy list env command for empty/missing envlist - by :user:`jugmac00`. (`#1987 <https://github.com/tox-dev/tox/issues/1987>`_)
- Requirements and constraints files handling got reimplemented, which should fix all open issues related to this area
  - by :user:`gaborbernat`. (`#1991 <https://github.com/tox-dev/tox/issues/1991>`_)
- Use importlib instead of ``__import__`` - by :user:`dmendek`. (`#1995 <https://github.com/tox-dev/tox/issues/1995>`_)
- Evaluate factor conditions for ``command`` keys - by :user:`jugmac00`. (`#2002 <https://github.com/tox-dev/tox/issues/2002>`_)
- Prefer f-strings instead of the str.format method - by :user:`eumiro`. (`#2012 <https://github.com/tox-dev/tox/issues/2012>`_)
- Fix regex validation for SHA 512 hashes - by :user:`jugmac00`. (`#2018 <https://github.com/tox-dev/tox/issues/2018>`_)
- Actually run all environments when ``ALL`` is provided to the legacy env command - by :user:`jugmac00`. (`#2112 <https://github.com/tox-dev/tox/issues/2112>`_)
- Move from ``appdirs`` to ``platformdirs`` - by :user:`gaborbernat`. (`#2117 <https://github.com/tox-dev/tox/issues/2117>`_)
- Move from ``toml`` to ``tomli`` - by :user:`gaborbernat`. (`#2118 <https://github.com/tox-dev/tox/issues/2118>`_)

Improved Documentation - 4.0.0a7
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Start documenting the plugin interface. Added :meth:`tox_register_tox_env <tox.plugin.spec.tox_register_tox_env>`,
  :meth:`tox_add_option <tox.plugin.spec.tox_add_option>`,
  :meth:`tox_add_core_config <tox.plugin.spec.tox_add_core_config>`,
  :meth:`tox_configure <tox.plugin.spec.tox_configure>` - by :user:`gaborbernat`. (`#1991 <https://github.com/tox-dev/tox/issues/1991>`_)
- Explain how ``-v`` and ``-q`` flags play together to determine CLI verbosity level - by :user:`jugmac00`. (`#2005 <https://github.com/tox-dev/tox/issues/2005>`_)
- Start polishing the documentation for the upcoming final release - by :user:`jugmac00`. (`#2006 <https://github.com/tox-dev/tox/issues/2006>`_)
- Update documentation about changelog entries for trivial changes - by :user:`jugmac00`. (`#2007 <https://github.com/tox-dev/tox/issues/2007>`_)


v4.0.0a6 (2021-02-15)
---------------------

Features - 4.0.0a6
~~~~~~~~~~~~~~~~~~
- Add basic quickstart implementation (just use pytest with the current Python version) - by :user:`gaborbernat`. (`#1829 <https://github.com/tox-dev/tox/issues/1829>`_)
- Support comments via the ``#`` character within the ini configuration (to force a literal ``#`` use ``\#``) -
  by :user:`gaborbernat`. (`#1831 <https://github.com/tox-dev/tox/issues/1831>`_)
- Add support for the ``install_command`` settings in the virtual env test environments - by :user:`gaborbernat`. (`#1832 <https://github.com/tox-dev/tox/issues/1832>`_)
- Add support for the ``package_root`` \ ``setupdir`` ( Python scoped) configuration that sets the root directory used for
  packaging (the location of the historical ``setup.py`` and modern ``pyproject.toml``). This can be set at root level, or
  at tox environment level (the later takes precedence over the former) - by :user:`gaborbernat`. (`#1838 <https://github.com/tox-dev/tox/issues/1838>`_)
- Implement support for the ``--installpkg`` CLI flag - by :user:`gaborbernat`. (`#1839 <https://github.com/tox-dev/tox/issues/1839>`_)
- Add support for the ``list_dependencies_command`` settings in the virtual env test environments - by
  :user:`gaborbernat`. (`#1842 <https://github.com/tox-dev/tox/issues/1842>`_)
- Add support for the ``ignore_errors`` settings in tox test environments - by :user:`gaborbernat`. (`#1843 <https://github.com/tox-dev/tox/issues/1843>`_)
- Add support for the ``pip_pre`` settings for virtual environment based tox environments - by :user:`gaborbernat`. (`#1844 <https://github.com/tox-dev/tox/issues/1844>`_)
- Add support for the ``platform`` settings in tox test environments - by :user:`gaborbernat`. (`#1845 <https://github.com/tox-dev/tox/issues/1845>`_)
- Add support for the ``recreate`` settings in tox test environments - by :user:`gaborbernat`. (`#1846 <https://github.com/tox-dev/tox/issues/1846>`_)
- Allow Python test and packaging environments with version 2.7 - by :user:`gaborbernat`. (`#1900 <https://github.com/tox-dev/tox/issues/1900>`_)
- Do not construct a requirements file for deps in virtualenv, instead pass content as CLI argument to pip - by
  :user:`gaborbernat`. (`#1906 <https://github.com/tox-dev/tox/issues/1906>`_)
- Do not display status update environment reports when interrupted or for the final environment ran (because at the
  final report will be soon printed and makes the status update redundant) - by :user:`gaborbernat`. (`#1909 <https://github.com/tox-dev/tox/issues/1909>`_)
- The ``_TOX_SHOW_THREAD`` environment variable can be used to print alive threads when tox exists (useful to debug
  when tox hangs because of some non-finished thread) and also now prints the pid of the local subprocess when reporting
  the outcome of a execution - by :user:`gaborbernat`. (`#1915 <https://github.com/tox-dev/tox/issues/1915>`_)

Bugfixes - 4.0.0a6
~~~~~~~~~~~~~~~~~~
- Normalize description text to collapse newlines and one or more than whitespace to a single space - by
  :user:`gaborbernat`. (`#1829 <https://github.com/tox-dev/tox/issues/1829>`_)
- Support aliases in show config key specification (will print with the primary key) - by :user:`gaborbernat`. (`#1831 <https://github.com/tox-dev/tox/issues/1831>`_)
- Show config no longer marks as unused keys that are inherited (e.g. if the key is coming from ``testenv`` section and our
  target is ``testenv:fix``) - by :user:`gaborbernat`. (`#1833 <https://github.com/tox-dev/tox/issues/1833>`_)
- ``--alwayscopy`` and ``--sitepackages`` legacy only flags do not work - by :user:`gaborbernat`. (`#1839 <https://github.com/tox-dev/tox/issues/1839>`_)
- Fix handling of ``commands_pre``/``commands``/``commands_post`` to be in line with tox 3 (returned incorrect exit codes
  and post was not always executed) - by :user:`gaborbernat`. (`#1843 <https://github.com/tox-dev/tox/issues/1843>`_)
- Support requirement files containing ``--hash`` constraints - by :user:`gaborbernat`. (`#1903 <https://github.com/tox-dev/tox/issues/1903>`_)
- Fix a bug that caused tox to never finish when pulling configuration from a tox run environment that was never executed
  - by :user:`gaborbernat`. (`#1915 <https://github.com/tox-dev/tox/issues/1915>`_)

Deprecations and Removals - 4.0.0a6
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- - Drop support for ``sdistsrc`` flag because introduces a significant complexity and is barely used (5 hits on a github
    search).
  - ``--skip-missing-interpreters``, ``--notest``, ``--sdistonly``, ``--installpkg``, ``--develop`` and
    ``--skip-pkg-install`` CLI flags are no longer available for ``devenv`` (enforce the only sane value for these).

  By :user:`gaborbernat` (`#1839 <https://github.com/tox-dev/tox/issues/1839>`_)
- Remove Jenkins override support: this feature goes against the spirit of tox - blurring the line between the CI and
  local runs. It also singles out a single CI provider, which opens the door for other CIs wanting similar functionality.
  Finally, only 54 code file examples came back on a Github search, showing this is a not widely used feature. People who
  still want Jenkins override support may create a tox plugin to achieve this functionality - by :user:`gaborbernat`. (`#1841 <https://github.com/tox-dev/tox/issues/1841>`_)


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
  with ``env PYTHONTRACEMALLOC=5 PYTHONDEVMODE=y`` under a Python built with ``--with-pydebug``)
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
- Rework how we handle Python packaging environments:

  - the base packaging environment changed from ``.package`` to ``.pkg``,
  - merged the ``sdist``, ``wheel`` and ``dev`` separate packaging implementations into one, and internally dynamically
    pick the one that's needed,
  - the base packaging environment always uses the same Python environment as tox is installed into,
  - the base packaging environment is used to get the metadata of the project (via PEP-517) and to build ``sdist`` and
    ``dev`` packages,
  - for building wheels introduced a new per env configurable option ``wheel_build_env``, if the target Python major/minor
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
