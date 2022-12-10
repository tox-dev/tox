Release History
===============
.. include:: _draft.rst

.. towncrier release notes start

v4.0.5 (2022-12-09)
-------------------

Bugfixes - 4.0.5
~~~~~~~~~~~~~~~~
- Normalize extra names passed in (fixes extra groups not being picked up during installation) - by :user:`gaborbernat`. (:issue:`2655`)


v4.0.4 (2022-12-09)
-------------------

Bugfixes - 4.0.4
~~~~~~~~~~~~~~~~
- Disable logging from ``distlib.util`` and ``filelock`` as these log messages are too verbose - by :user:`gaborbernat`. (:issue:`2655`)
- Use ``!r`` and ``repr()`` to better display erroneous values in exception from ``StrConverter.to_bool()`` - by :user:`ptmcg`. (:issue:`2665`)

Improved Documentation - 4.0.4
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Document that running ``--showconfig`` or ``--help-ini`` with the ``-v`` flag will add interleaved debugging
  information, whereas tox v3 added extra lines at the start  - by :user:`jugmac00`. (:issue:`2622`)
- Document that tox v4 errors when using ``-U`` when defining dependencies via ``deps``  - by :user:`jugmac00`. (:issue:`2631`)


v4.0.3 (2022-12-08)
-------------------

Bugfixes - 4.0.3
~~~~~~~~~~~~~~~~
- Always set environment variable ``PYTHONIOENCODING`` to ``utf-8`` to ensure tox works under Windows custom encodings
  - by :user:`gaborbernat`. (:issue:`2422`)
- Ensure :ref:`change_dir` is created if does not exist before executing :ref:`commands` - by :user:`gaborbernat`. (:issue:`2620`)
- Pass through ``NUMBER_OF_PROCESSORS`` on Windows as is needed for ``multiprocessing.cpu_count`` -
  by :user:`gaborbernat`. (:issue:`2629`)
- The core tox configuration now contains ``host_python`` key showing the host python executable path -
  by :user:`gaborbernat`. (:issue:`2630`)

Improved Documentation - 4.0.3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Document that space separator is no longer valid for the :ref:`passenv` and instead one should use comma  -
  by :user:`gaborbernat`. (:issue:`2615`)
- Document necessity to escape ``#`` within INI configuration - by :user:`jugmac00`. (:issue:`2617`)


v4.0.2 (2022-12-07)
-------------------

Bugfixes - 4.0.2
~~~~~~~~~~~~~~~~
- Unescaped comma in substitution should not be replaced during INI expansion - by :user:`gaborbernat`. (:issue:`2616`)
- ``tox --showconfig -e py311`` reports tox section, though it should not - by :user:`gaborbernat`. (:issue:`2624`)


v4.0.1 (2022-12-07)
-------------------

Bugfixes - 4.0.1
~~~~~~~~~~~~~~~~
- Create session views of the build wheel/sdist into the :ref:`temp_dir` folder - by :user:`gaborbernat`. (:issue:`2612`)
- Default tox min_version to 4.0 instead of current tox version - by :user:`gaborbernat`. (:issue:`2613`)


v4.0.0 (2022-12-07)
-------------------

Bugfixes - 4.0.0
~~~~~~~~~~~~~~~~
- The temporary folder within the tox environment was named ``.temp`` instead of ``.tmp`` - by :user:`gaborbernat`. (:issue:`2608`)

Improved Documentation - 4.0.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Enumerate breaking changes of tox 4 in the FAQ, and also list major new improvements - by :user:`gaborbernat`. (:issue:`2587`)
- Document in the FAQ that tox 4 will raise a warning when finding conflicting environment names - by :user:`gaborbernat`. (:issue:`2602`)


v4.0.0rc4 (2022-12-06)
----------------------

Bugfixes - 4.0.0rc4
~~~~~~~~~~~~~~~~~~~
- Fix extras not being kept for install dependencies - by :user:`gaborbernat`. (:issue:`2603`)

Deprecations and Removals - 4.0.0rc4
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Remove deprecated configuration option ``whitelist_externals`` which was replaced by ``allowlist_externals`` - by :user:`jugmac00`. (:issue:`2599`)


v4.0.0rc3 (2022-12-05)
----------------------

Features - 4.0.0rc3
~~~~~~~~~~~~~~~~~~~
- Add ``--exit-and-dump-after`` flag that allows automatically killing tox if does not finish within the passed seconds,
  and dump the thread stacks (useful to debug tox when it seemingly hangs) - by :user:`gaborbernat`. (:issue:`2595`)

Bugfixes - 4.0.0rc3
~~~~~~~~~~~~~~~~~~~
- Ensure that two parallel tox instance invocations on different tox environment targets will work by holding a file lock
  onto the packaging operations (e.g., in bash ``tox4 r -e py311 &; tox4 r -e py310``) - by :user:`gaborbernat`. (:issue:`2594`)
- Fix leaking backend processes when the build backend does not support editable wheels and fix failure when multiple
  environments exist that have a build backend that does not support editable wheels - by :user:`gaborbernat`. (:issue:`2595`)


v4.0.0rc2 (2022-12-04)
----------------------

Features - 4.0.0rc2
~~~~~~~~~~~~~~~~~~~
- Support for recursive extras in Python package dependencies - by :user:`gaborbernat`. (:issue:`2567`)

Bugfixes - 4.0.0rc2
~~~~~~~~~~~~~~~~~~~
- Support in INI files for ignore exit code marker the ``-`` without a subsequent space too - by :user:`gaborbernat`. (:issue:`2561`)
- Ensure paths constructed by tox are stable by resolving relative paths to fully qualified one, this insures that running
  tox from a different folder than project root still generates meaningful paths - by :user:`gaborbernat`. (:issue:`2562`)
- Ensure only on run environment operates at a time on a packaging environment (fixes unexpected failures when running in
  parallel mode) - by :user:`gaborbernat`. (:issue:`2564`)
- Fallback to ``editable-legacy`` if package target is ``editable`` but the build backend does not have ``build_editable``
  hook - by :user:`gaborbernat`. (:issue:`2567`)
- Allow reference replacement in INI configuration via keys that contain the ``-`` character - by :user:`gaborbernat`. (:issue:`2569`)
- Resolve symlinks when saving Python executable path - by :user:`ssbarnea`. (:issue:`2574`)
- Do not set ``COLUMNS`` or ``LINES`` environment to the current TTY size if already set by the user -
  by :user:`gaborbernat`. (:issue:`2575`)
- Add missing :pypi:`build[virtualenv]<build>` test dependency - by :user:`ssbarnea`. (:issue:`2576`)


v4.0.0rc1 (2022-11-29)
----------------------

Features - 4.0.0rc1
~~~~~~~~~~~~~~~~~~~
- Add support for generative section headers - by :user:`gaborbernat`. (:issue:`2362`)

Bugfixes - 4.0.0rc1
~~~~~~~~~~~~~~~~~~~
- Allow installing relative paths that go outside tox root folder. - by :user:`ssbarnea`. (:issue:`2366`)


v4.0.0b3 (2022-11-27)
---------------------

Features - 4.0.0b3
~~~~~~~~~~~~~~~~~~
- Improve coloring of logged commands - by :user:`ssbarnea`. (:issue:`2356`)
- Pass ``PROGRAMDATA``,  ``PROGRAMFILES(x86)``, ``PROGRAMFILES`` environments on Windows by default as it is needed for discovering the VS C++ compiler and start testing against 3.11 - by :user:`gaborbernat`. (:issue:`2492`)
- Support PEP-621 static metadata for getting package dependencies - by :user:`gaborbernat`. (:issue:`2499`)
- Add support for editable wheels, make it the default development mode and rename ``dev-legacy`` mode to
  ``editable-legacy`` - by :user:`gaborbernat`. (:issue:`2502`)

Bugfixes - 4.0.0b3
~~~~~~~~~~~~~~~~~~
- Recognize ``TERM=dumb`` or ``NO_COLOR`` environment variables. - by :user:`ssbarnea`. (:issue:`1290`)
- Allow passing config directory without filename. - by :user:`ssbarnea`. (:issue:`2340`)
- Avoid ignored explicit argument 're' console message. - by :user:`ssbarnea`. (:issue:`2342`)
- Display registered plugins with ``tox --version`` - by :user:`mxd4`. (:issue:`2358`)
- Allow ``--hash`` to be specified in requirements.txt files. - by :user:`masenf`. (:issue:`2373`)
- Avoid impossible minversion version requirements. - by :user:`ssbarnea`. (:issue:`2414`)

Improved Documentation - 4.0.0b3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add new documentation for tox 4 - by :user:`gaborbernat`. (:issue:`2408`)


v4.0.0b2 (2022-04-11)
---------------------

Features - 4.0.0b2
~~~~~~~~~~~~~~~~~~
- Use ``tox`` console entry point name instead of ``tox4`` - by :user:`gaborbernat`. (:issue:`2344`)
- Use ``.tox`` as working directory instead of ``.tox/4`` - by :user:`gaborbernat`. (:issue:`2346`)
- Switch to ``hatchling`` as build backend instead of ``setuptools`` - by :user:`gaborbernat`. (:issue:`2368`)

Bugfixes - 4.0.0b2
~~~~~~~~~~~~~~~~~~
- Fix CLI raises an error for ``-va`` with ``ignored explicit argument 'a'`` - by :user:`gaborbernat`. (:issue:`2343`)
- Do not interpolate values when parsing ``tox.ini`` configuration files - by :user:`gaborbernat`. (:issue:`2350`)

Improved Documentation - 4.0.0b2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Deleted the tox mailing list -- by :user:`jugmac00` (:issue:`2364`)


v4.0.0b1 (2022-02-05)
---------------------

Features - 4.0.0b1
~~~~~~~~~~~~~~~~~~
- Display a hint for unrecognized argument CLI parse failures to use ``--`` separator to pass arguments to commands
  - by :user:`gaborbernat`. (:issue:`2183`)
- Do not allow extending the config set beyond setup to ensures that all configuration values are visible via the config
  sub-command. - by :user:`gaborbernat`. (:issue:`2243`)
- Print a message when ignoring outcome of commands - by :user:`gaborbernat`. (:issue:`2315`)

Bugfixes - 4.0.0b1
~~~~~~~~~~~~~~~~~~
- Fix type annotation is broken for :meth:`tox.config.sets.ConfigSet.add_config` when adding a container type
  - by :user:`gaborbernat`. (:issue:`2233`)
- Insert ``TOX_WORK_DIR``, ``TOX_ENV_NAME``, ``TOX_ENV_DIR`` and ``VIRTUAL_ENV`` into the environment variables for all
  tox environments to keep contract with tox version 3 - by :user:`gaborbernat`. (:issue:`2259`)
- Fix plugin initialization order - core plugins first, then 3rd party and finally inline - by :user:`gaborbernat`. (:issue:`2264`)
- Legacy parallel mode should accept ``-p`` flag without arguments - by :user:`gaborbernat`. (:issue:`2299`)
- Sequential run fails because the packaging environment is deleted twice for sequential runs with recreate flag on
  - by :user:`gaborbernat`. (:issue:`2300`)
- Require Python 3.10 to generate docs - by :user:`jugmac00`. (:issue:`2321`)
- Environment assignment for output breaks when using ``-rv`` (when we cannot guess upfront the verbosity level from the
  CLI arguments) - by :user:`gaborbernat`. (:issue:`2324`)
- ``devenv`` command does not respect specified path - by :user:`gaborbernat`. (:issue:`2325`)

Improved Documentation - 4.0.0b1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Enable link check during documentation build - by :user:`gaborbernat`. (:issue:`806`)
- Document ownership of the ``tox.wiki`` root domain - by :user:`gaborbernat`. (:issue:`2242`)
- Document :meth:`tox.config.sets.ConfigSet.loaders` - by :user:`gaborbernat`. (:issue:`2287`)
- Fix CLI documentation is missing and broken documentation references - by :user:`gaborbernat`. (:issue:`2310`)


v4.0.0a10 (2022-01-04)
----------------------

Features - 4.0.0a10
~~~~~~~~~~~~~~~~~~~
- Support for grouping environment values together by applying labels to them either at :ref:`core <labels>` and
  :ref:`environment <labels-env>` level, and allow selecting them via the :ref:`-m <tox-run--m>` flag from the CLI - by
  :user:`gaborbernat`. (:issue:`238`)
- Support for environment files within the :ref:`set_env` configuration via the ``file|`` prefix - by :user:`gaborbernat`. (:issue:`1938`)
- Support for ``--no-provision`` flag - by :user:`gaborbernat`. (:issue:`1951`)
- Missing ``pyproject.toml`` or ``setup.py`` file at the tox root folder without the ``--install-pkg`` flag assumes no
  packaging - by :user:`gaborbernat`. (:issue:`1964`)
- Add ``external`` package type for :ref:`package` (see :ref:`external-package-builder`), and extract package dependencies
  for packages passed in via :ref:`--installpkg <tox-run---installpkg>` - by :user:`gaborbernat`. (:issue:`2204`)
- Add support for rewriting script invocations that have valid shebang lines when the ``TOX_LIMITED_SHEBANG`` environment
  variable is set and not empty - by :user:`gaborbernat`. (:issue:`2208`)
- Support for the ``--discover`` CLI flag - by :user:`gaborbernat`. (:pull:`2245`)
- Moved the python packaging logic into a dedicate package :pypi:`pyproject-api` and
  use it as a dependency - by :user:`gaborbernat`. (:pull:`2274`)
- Drop python 3.6 support - by :user:`gaborbernat`. (:pull:`2275`)
- Support for selecting target environments with a given factor via the :ref:`-f <tox-run--f>` CLI environment flag - by
  :user:`gaborbernat`. (:pull:`2290`)

Bugfixes - 4.0.0a10
~~~~~~~~~~~~~~~~~~~
- Fix ``CTRL+C`` is not stopping the process on Windows - by :user:`gaborbernat`. (:issue:`2159`)
- Fix list/depends commands can create tox package environment as runtime environment and display an error message
  - by :user:`gaborbernat`. (:pull:`2234`)

Deprecations and Removals - 4.0.0a10
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- ``tox_add_core_config`` and ``tox_add_env_config`` now take a ``state: State`` argument instead of a configuration one,
  and ``Config`` not longer provides the ``envs`` property (instead users should migrate to ``State.envs``) - by
  :user:`gaborbernat`. (:pull:`2275`)


v4.0.0a9 (2021-09-16)
---------------------

Features - 4.0.0a9
~~~~~~~~~~~~~~~~~~
- Expose the parsed CLI arguments on the main configuration object for plugins and allow plugins to define their own
  configuration section -- by :user:`gaborbernat`. (:pull:`2191`)
- Let tox run fail when all envs are skipped -- by :user:`jugmac00`. (:issue:`2195`)
- Expose the configuration loading mechanism to plugins to define and load their own sections. Add
  :meth:`tox_add_env_config <tox.plugin.spec.tox_add_env_config>` plugin hook called after the configuration environment
  is created for a tox environment and removed ``tox_configure``. Add the main configuration object as argument to
  :meth:`tox_add_core_config <tox.plugin.spec.tox_add_core_config>`. Move the environment list method from the state to
  the main configuration object to allow its use within plugins -- by :user:`gaborbernat`. (:issue:`2200`)
- Allow running code in plugins before and after commands via
  :meth:`tox_before_run_commands <tox.plugin.spec.tox_before_run_commands>` and
  :meth:`tox_after_run_commands <tox.plugin.spec.tox_after_run_commands>` plugin points -- by :user:`gaborbernat`. (:issue:`2201`)
- Allow plugins to update the :ref:`set_env` and change the :ref:`pass_env` configurations -- by :user:`gaborbernat`. (:issue:`2215`)

Bugfixes - 4.0.0a9
~~~~~~~~~~~~~~~~~~
- Fix env variable substitutions with defaults containing colon (e.g. URL) -- by :user:`comabrewer`. (:issue:`2182`)
- Do not allow constructing ``ConfigSet`` directly and implement ``__contains__`` for ``Loader`` -- by
  :user:`gaborbernat`. (:pull:`2209`)
- Fix old-new value on recreate cache miss-match are swapped -- by :user:`gaborbernat`. (:issue:`2211`)
- Report fails when report does not support Unicode characters -- by :user:`gaborbernat`. (:issue:`2213`)

Improved Documentation - 4.0.0a9
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Adopt furo theme, update our state diagram and description in user docs (SVG + light/dark variant), split
  the Python API into its own page from under the plugin page, and document plugin adoption under the ``tox-dev``
  organization - by :user:`gaborbernat`. (:issue:`1881`)


v4.0.0a8 (2021-08-21)
---------------------

Features - 4.0.0a8
~~~~~~~~~~~~~~~~~~
- Add support for :ref:`allowlist_externals`, commands not matching error - by :user:`gaborbernat`. (:issue:`1127`)
- Add outcome of environments into the result json (:ref:`--result-json <tox-run---result-json>`) under the ``result`` key
  containing ``success`` boolean, ``exit_code`` integer and ``duration`` float value  - by :user:`gaborbernat`. (:issue:`1405`)
- Add ``exec`` subcommand that allows users to run an arbitrary command within the tox environment (without needing to
  modify their configuration) - by :user:`gaborbernat`. (:issue:`1790`)
- Add check to validate the base Python names and the environments name do not conflict Python spec wise, when they do
  raise error if :ref:`ignore_base_python_conflict` is not set or ``False`` - by :user:`gaborbernat`. (:issue:`1840`)
- Allow any Unix shell-style wildcards expression for  :ref:`pass_env` - by :user:`gaborbernat`. (:issue:`2121`)
- Add support for :ref:`args_are_paths` flag - by :user:`gaborbernat`. (:issue:`2122`)
- Add support for :ref:`env_log_dir` (compared to tox 3 extend content and keep only last run entries) -
  by :user:`gaborbernat`. (:issue:`2123`)
- Add support for ``{:}`` substitution in ini files as placeholder for the OS path separator - by :user:`gaborbernat`. (:issue:`2125`)
- When cleaning directories (for tox environment, ``env_log_dir``, ``env_tmp_dir`` and packaging metadata folders) do not
  delete the directory itself and recreate, but instead just delete its content (this allows the user to cd into it and
  still be in a valid folder after a new run) - by :user:`gaborbernat`. (:pull:`2139`)
- Changes to help plugin development: simpler tox env creation argument list, expose python creation directly,
  allow skipping list dependencies install command for pip and executable is only part of the python cache for virtualenv
  - by :user:`gaborbernat`. (:pull:`2172`)

Bugfixes - 4.0.0a8
~~~~~~~~~~~~~~~~~~
- Support ``#`` character in path for the tox project - by :user:`gaborbernat`. (:issue:`763`)
- If the command expression fails to parse with shlex fallback to literal pass through of the remaining elements
  - by :user:`gaborbernat`. (:issue:`1944`)
- tox config fails on :ref:`--recreate <tox-config---recreate>` flag, and once specified the output does not reflect the
  impact of the CLI flags - by :user:`gaborbernat`. (:issue:`2037`)
- Virtual environment creation for Python is always triggered at every run - by :user:`gaborbernat`. (:issue:`2041`)
- Add support for setting :ref:`suicide_timeout`, :ref:`interrupt_timeout` and :ref:`terminate_timeout` - by
  :user:`gaborbernat`. (:issue:`2124`)
- Parallel show output not working when there's a packaging phase in the run - by :user:`gaborbernat`. (:pull:`2161`)

Improved Documentation - 4.0.0a8
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Note constraint files are a subset of requirement files - by :user:`gaborbernat`. (:issue:`1939`)
- Add a note about having a package with different Python requirements than tox and not specifying :ref:`base_python` -
  by :user:`gaborbernat`. (:issue:`1975`)
- Fix :ref:`--runner <tox---runner>` is missing default value and documentation unclear - by :user:`gaborbernat`. (:issue:`2004`)


v4.0.0a7 (2021-07-28)
---------------------

Features - 4.0.0a7
~~~~~~~~~~~~~~~~~~
- Add support for configuration taken from the ``setup.cfg`` file -by :user:`gaborbernat`. (:issue:`1836`)
- Add support for configuration taken from the ``pyproject.toml`` file, ``tox`` section ``legacy_tox_ini`` key - by
  :user:`gaborbernat`. (:issue:`1837`)
- Add configuration documentation - by :user:`gaborbernat`. (:issue:`1914`)
- Implemented ``[]`` substitution (alias for ``{posargs}``) - by
  :user:`hexagonrecursion`. (:issue:`1928`)
- Implement ``[testenv] ignore_outcome`` - "a failing result of this testenv will not make tox fail" - by :user:`hexagonrecursion`. (:issue:`1947`)
- Inline plugin support via ``tox_.py``. This is loaded where the tox config source is discovered. It's a Python file
  that can contain arbitrary Python code, such as definition of a plugin. Eventually we'll add a plugin that allows
  succinct declaration/generation of new tox environments - by :user:`gaborbernat`. (:pull:`1963`)
- Introduce the installer concept, and collect pip installation into a ``pip`` package, also attach to this
  the requirements file parsing which got a major rework - by :user:`gaborbernat`. (:pull:`1991`)
- Support CPython ``3.10`` -by :user:`gaborbernat`. (:pull:`2014`)

Bugfixes - 4.0.0a7
~~~~~~~~~~~~~~~~~~
- Environments with a platform mismatch are no longer silently skipped, but properly reported - by :user:`jugmac00`. (:issue:`1926`)
- Port pip requirements file parser to ``tox`` to achieve full equivalency (such as support for the per requirement
  ``--install-option`` and ``--global-option`` flags) - by :user:`gaborbernat`. (:issue:`1929`)
- Support for extras with paths for Python deps and requirement files - by :user:`gaborbernat`. (:issue:`1933`)
- Due to a bug ``\{posargs} {posargs}`` used to expand to literal ``{posargs} {posargs}``.
  Now the second ``{posargs}`` is expanded.
  ``\{posargs} {posargs}`` expands to ``{posargs} positional arguments here`` - by :user:`hexagonrecursion`. (:issue:`1956`)
- Enable setting a different ``upstream`` repository for the coverage diff report.
  This has been hardcoded to ``upstream/rewrite`` until now.
  by :user:`jugmac00`. (:issue:`1972`)
- Enable replacements (a.k.a section substitutions) for section names containing a dash in sections
  without the ``testenv:`` prefix - by :user:`jugmac00`, :user:`obestwalter`, :user:`eumiro`. (:issue:`1985`)
- Fix legacy list env command for empty/missing envlist - by :user:`jugmac00`. (:issue:`1987`)
- Requirements and constraints files handling got reimplemented, which should fix all open issues related to this area
  - by :user:`gaborbernat`. (:pull:`1991`)
- Use importlib instead of ``__import__`` - by :user:`dmendek`. (:issue:`1995`)
- Evaluate factor conditions for ``command`` keys - by :user:`jugmac00`. (:issue:`2002`)
- Prefer f-strings instead of the str.format method - by :user:`eumiro`. (:issue:`2012`)
- Fix regex validation for SHA 512 hashes - by :user:`jugmac00`. (:issue:`2018`)
- Actually run all environments when ``ALL`` is provided to the legacy env command - by :user:`jugmac00`. (:issue:`2112`)
- Move from ``appdirs`` to ``platformdirs`` - by :user:`gaborbernat`. (:pull:`2117`)
- Move from ``toml`` to ``tomli`` - by :user:`gaborbernat`. (:pull:`2118`)

Improved Documentation - 4.0.0a7
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Start documenting the plugin interface. Added :meth:`tox_register_tox_env <tox.plugin.spec.tox_register_tox_env>`,
  :meth:`tox_add_option <tox.plugin.spec.tox_add_option>`,
  :meth:`tox_add_core_config <tox.plugin.spec.tox_add_core_config>`,
  ``tox_configure`` - by :user:`gaborbernat`. (:pull:`1991`)
- Explain how ``-v`` and ``-q`` flags play together to determine CLI verbosity level - by :user:`jugmac00`. (:issue:`2005`)
- Start polishing the documentation for the upcoming final release - by :user:`jugmac00`. (:pull:`2006`)
- Update documentation about changelog entries for trivial changes - by :user:`jugmac00`. (:issue:`2007`)


v4.0.0a6 (2021-02-15)
---------------------

Features - 4.0.0a6
~~~~~~~~~~~~~~~~~~
- Add basic quickstart implementation (just use pytest with the current Python version) - by :user:`gaborbernat`. (:issue:`1829`)
- Support comments via the ``#`` character within the ini configuration (to force a literal ``#`` use ``\#``) -
  by :user:`gaborbernat`. (:issue:`1831`)
- Add support for the ``install_command`` settings in the virtual env test environments - by :user:`gaborbernat`. (:issue:`1832`)
- Add support for the ``package_root`` \ ``setupdir`` ( Python scoped) configuration that sets the root directory used for
  packaging (the location of the historical ``setup.py`` and modern ``pyproject.toml``). This can be set at root level, or
  at tox environment level (the later takes precedence over the former) - by :user:`gaborbernat`. (:issue:`1838`)
- Implement support for the ``--installpkg`` CLI flag - by :user:`gaborbernat`. (:issue:`1839`)
- Add support for the ``list_dependencies_command`` settings in the virtual env test environments - by
  :user:`gaborbernat`. (:issue:`1842`)
- Add support for the ``ignore_errors`` settings in tox test environments - by :user:`gaborbernat`. (:issue:`1843`)
- Add support for the ``pip_pre`` settings for virtual environment based tox environments - by :user:`gaborbernat`. (:issue:`1844`)
- Add support for the ``platform`` settings in tox test environments - by :user:`gaborbernat`. (:issue:`1845`)
- Add support for the ``recreate`` settings in tox test environments - by :user:`gaborbernat`. (:issue:`1846`)
- Allow Python test and packaging environments with version 2.7 - by :user:`gaborbernat`. (:pull:`1900`)
- Do not construct a requirements file for deps in virtualenv, instead pass content as CLI argument to pip - by
  :user:`gaborbernat`. (:pull:`1906`)
- Do not display status update environment reports when interrupted or for the final environment ran (because at the
  final report will be soon printed and makes the status update redundant) - by :user:`gaborbernat`. (:issue:`1909`)
- The ``_TOX_SHOW_THREAD`` environment variable can be used to print alive threads when tox exists (useful to debug
  when tox hangs because of some non-finished thread) and also now prints the pid of the local subprocess when reporting
  the outcome of an execution - by :user:`gaborbernat`. (:pull:`1915`)

Bugfixes - 4.0.0a6
~~~~~~~~~~~~~~~~~~
- Normalize description text to collapse newlines and one or more than whitespace to a single space - by
  :user:`gaborbernat`. (:issue:`1829`)
- Support aliases in show config key specification (will print with the primary key) - by :user:`gaborbernat`. (:issue:`1831`)
- Show config no longer marks as unused keys that are inherited (e.g. if the key is coming from ``testenv`` section and our
  target is ``testenv:fix``) - by :user:`gaborbernat`. (:issue:`1833`)
- ``--alwayscopy`` and ``--sitepackages`` legacy only flags do not work - by :user:`gaborbernat`. (:issue:`1839`)
- Fix handling of ``commands_pre``/``commands``/``commands_post`` to be in line with tox 3 (returned incorrect exit codes
  and post was not always executed) - by :user:`gaborbernat`. (:issue:`1843`)
- Support requirement files containing ``--hash`` constraints - by :user:`gaborbernat`. (:issue:`1903`)
- Fix a bug that caused tox to never finish when pulling configuration from a tox run environment that was never executed
  - by :user:`gaborbernat`. (:pull:`1915`)

Deprecations and Removals - 4.0.0a6
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- - Drop support for ``sdistsrc`` flag because introduces a significant complexity and is barely used (5 hits on a github
    search).
  - ``--skip-missing-interpreters``, ``--notest``, ``--sdistonly``, ``--installpkg``, ``--develop`` and
    ``--skip-pkg-install`` CLI flags are no longer available for ``devenv`` (enforce the only sane value for these).

  By :user:`gaborbernat` (:issue:`1839`)
- Remove Jenkins override support: this feature goes against the spirit of tox - blurring the line between the CI and
  local runs. It also singles out a single CI provider, which opens the door for other CIs wanting similar functionality.
  Finally, only 54 code file examples came back on a Github search, showing this is a not widely used feature. People who
  still want Jenkins override support may create a tox plugin to achieve this functionality - by :user:`gaborbernat`. (:issue:`1841`)


v4.0.0a5 (2021-01-23)
---------------------

Features - 4.0.0a5
~~~~~~~~~~~~~~~~~~
- Support the ``system_site_packages``/``sitepackages`` flag for virtual environment based tox environments -
  by :user:`gaborbernat`. (:issue:`1847`)
- Support the ``always_copy``/``alwayscopy`` flag for virtual environment based tox environments -
  by :user:`gaborbernat`. (:issue:`1848`)
- Support the ``download`` flag for virtual environment based tox environments - by :user:`gaborbernat`. (:issue:`1849`)
- Recreate virtual environment based tox environments when the ``virtualenv`` version changes - by :user:`gaborbernat`. (:issue:`1865`)

Bugfixes - 4.0.0a5
~~~~~~~~~~~~~~~~~~
- Not all package dependencies are installed when different tox environments in the same run use different set of
  extras - by :user:`gaborbernat`. (:issue:`1868`)
- Support ``=`` separator in requirement file flags, directories as requirements and correctly set the root of the
  requirements file when using the ``--root`` CLI flag to change the root - by :user:`gaborbernat`. (:issue:`1853`)
- Cleanup local subprocess file handlers when exiting runs (fixes ``ResourceWarning: unclosed file`` errors when running
  with ``env PYTHONTRACEMALLOC=5 PYTHONDEVMODE=y`` under a Python built with ``--with-pydebug``)
  - by :user:`gaborbernat`. (:issue:`1857`)
- Various small bugfixes:

  - honor updating default environment variables set by internal tox via set env (``PIP_DISABLE_PIP_VERSION_CHECK``)
  - do not multi-wrap ``HandledError`` in the ini file loader,
  - skipped environments are logged now with their fail message at default verbosity level,
  - fix an error that made the show configuration command crash when making the string of a config value failed,
  - support empty-new lines within the set env configurations replacements,

  by :user:`gaborbernat`. (:pull:`1864`)

Improved Documentation - 4.0.0a5
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add CLI documentation - by :user:`gaborbernat`. (:pull:`1852`)


v4.0.0a4 (2021-01-16)
---------------------

Features - 4.0.0a4
~~~~~~~~~~~~~~~~~~
- Use ``.tox/4`` instead of ``.tox4`` folder (so ignores for tox 3 works for tox 4 too), reminder we'll rename this to
  just ``.tox`` before public release, however to encourage testing tox 4 in parallel with tox 3 this is helpful
  - by :user:`gaborbernat`. (:discussion:`1812`)
- Colorize the ``config`` command: section headers are yellow, keys are green, values remained white, exceptions are light
  red and comments are cyan - by :user:`gaborbernat`. (:pull:`1821`)

Bugfixes - 4.0.0a4
~~~~~~~~~~~~~~~~~~
- Support legacy format (``-cconstraint.txt``) of constraint files in ``deps``, and expand constraint files too when
  viewing inside the ``deps`` or calculating weather our environment is up to date or not - by :user:`gaborbernat`. (:issue:`1788`)
- When specifying requirements/editable/constraint paths within ``deps`` escape space, unless already escaped to support
  running specifying transitive requirements files within deps - by :user:`gaborbernat`. (:issue:`1792`)
- When using a provisioned tox environment requesting ``--recreate`` failed with ``AttributeError`` -
  by :user:`gaborbernat`. (:issue:`1793`)
- Fix ``RequirementsFile`` from tox is rendered incorrectly in ``config`` command - by :user:`gaborbernat`. (:issue:`1820`)
- Fix a bug in the configuration system where referring to the same named key in another env/section causes circular
  dependency error - by :user:`gaborbernat`. (:pull:`1821`)
- Raise ``ValueError`` with descriptive message when a requirements file specified does not exist
  - by :user:`gaborbernat`. (:pull:`1828`)
- Support all valid requirement file specification without delimiting space in the ``deps`` of the ``tox.ini`` -
  by :user:`gaborbernat`. (:issue:`1834`)

Improved Documentation - 4.0.0a4
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add code style guide for contributors - by :user:`gaborbernat`. (:issue:`1734`)


v4.0.0a3 (2021-01-13)
---------------------

Features - 4.0.0a3
~~~~~~~~~~~~~~~~~~
- Raise exception when set env enters into a circular reference - by :user:`gaborbernat`. (:issue:`1779`)
- - Raise exception when variable substitution enters into a circle.
  - Add ``{/}`` as substitution for os specific path separator.
  - Add ``{env_bin_dir}`` constant substitution.
  - Implement support for ``--discover`` flag - by :user:`gaborbernat`. (:pull:`1784`)

Bugfixes - 4.0.0a3
~~~~~~~~~~~~~~~~~~
- Entries in the ``set_env`` does not reference environments from ``set_env`` - by :user:`gaborbernat`. (:issue:`1776`)
- ``env`` substitution does not uses values from ``set_env`` - by :user:`gaborbernat`. (:issue:`1779`)
- Adopt tox 3 base pass env list, by adding:

  - on all platforms: ``LANG``, ``LANGUAGE``, ``CURL_CA_BUNDLE``, ``SSL_CERT_FILE`` , ``LD_LIBRARY_PATH`` and ``REQUESTS_CA_BUNLDE``,
  - on Windows: ``SYSTEMDRIVE`` - by :user:`gaborbernat`. (:issue:`1780`)
- Fixed a bug that crashed tox where calling tox with the recreate flag and when multiple environments were reusing the
  same package - by :user:`gaborbernat`. (:issue:`1782`)
- - Python version markers are stripped in package dependencies (after wrongfully being detected as an extra marker).
  - In packaging APIs do not set ``PYTHONPATH`` (to empty string) if ``backend-path`` is empty.
  - Fix commands parsing on Windows (do not auto-escape ``\`` - instead users should use the new ``{\}``, and on parsed
    arguments strip both ``'`` and ``"`` quoted outcomes).
  - Allow windows paths in substitution set/default (the ``:`` character used to separate substitution arguments may
    also be present in paths on Windows - do not support single capital letter values as substitution arguments) -
    by :user:`gaborbernat`. (:pull:`1784`)
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

  by :user:`gaborbernat`. (:issue:`1804`)


v4.0.0a2 (2021-01-09)
---------------------

Features - 4.0.0a2
~~~~~~~~~~~~~~~~~~
- Add option to disable colored output, and support ``NO_COLOR`` and ``FORCE_COLOR`` environment variables - by
  :user:`gaborbernat`. (:pull:`1630`)

Bugfixes - 4.0.0a2
~~~~~~~~~~~~~~~~~~
- Fix coverage generation in CI - by :user:`gaborbernat`. (:pull:`1551`)
- Fix the CI failures:

  - drop Python 3.5 support as it's not expected to get to a release before EOL,
  - fix test using ``\n`` instead of ``os.linesep``,
  - Windows Python 3.6 does not contain ``_overlapped.ReadFileInto``

  - by :user:`gaborbernat`. (:pull:`1556`)

Improved Documentation - 4.0.0a2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add base documentation by merging virtualenv structure with tox 3 - by :user:`gaborbernat`. (:pull:`1551`)


v4.0.0a1
--------
* First version all is brand new.

.. warning::

   The current tox is the second iteration of implementation. From version ``0.5`` all the way to ``3.X``
   we numbered the first iteration. Version ``4.0.0a1`` is a complete rewrite of the package, and as such this release
   history starts from there. The old changelog is still available in the
   `legacy branch documentation <https://tox.wiki/en/stable/changelog.html>`_.
