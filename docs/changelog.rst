Release History
===============
.. include:: _draft.rst

.. towncrier release notes start

v4.25.0 (2025-03-27)
--------------------

Features - 4.25.0
~~~~~~~~~~~~~~~~~
- Add support for number ranges in generative environments, more details :ref:`here<generative-environment-list>`. - by :user:`mimre25` (:issue:`3502`)

Bugfixes - 4.25.0
~~~~~~~~~~~~~~~~~
- Make tox tests pass with Python 3.14.0a6
  - by :user:`hroncok` (:issue:`3500`)

v4.24.2 (2025-03-07)
--------------------

Bugfixes - 4.24.2
~~~~~~~~~~~~~~~~~
- multiple source_type supports for the same filename. Like pyproject.toml can be load by both TomlPyProject & LegacyToml (:issue:`3117`)
- Support ``set_env = { file = "conf{/}local.env"}`` for TOML format - by :user:`juditnovak`. (:issue:`3474`)
- fix example on the docs (:issue:`3480`)
- - ``--parallel-no-spinner`` now respects max CPU set by ``--parallel N`` (:issue:`3495`)

Improved Documentation - 4.24.2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Updates the documentation for ``os.environ['KEY']`` when the variable does not exist - by :user:`jugmac00`. (:issue:`3456`)

v4.24.1 (2025-01-21)
--------------------

Misc - 4.24.1
~~~~~~~~~~~~~
- :issue:`3426`

v4.24.0 (2025-01-21)
--------------------

Features - 4.24.0
~~~~~~~~~~~~~~~~~
- Add a ``schema`` command to produce a JSON Schema for tox and the current plugins.

  - by :user:`henryiii` (:issue:`3446`)

Bugfixes - 4.24.0
~~~~~~~~~~~~~~~~~
- Log exception name when subprocess execution produces one.

  - by :user:`ssbarnea` (:issue:`3450`)

Improved Documentation - 4.24.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Fix typo in ``docs/config.rst`` from ``{}`` to ``{:}``.

  - by :user:`wooshaun53` (:issue:`3424`)
- Pass ``NIX_LD`` and ``NIX_LD_LIBRARY_PATH`` variables by default in ``pass_env`` to make generic binaries work under Nix/NixOS.

  - by :user:`albertodonato` (:issue:`3425`)

v4.23.2 (2024-10-22)
--------------------

Misc - 4.23.2
~~~~~~~~~~~~~
- :issue:`3415`

v4.23.1 (2024-10-21)
--------------------

Improved Documentation - 4.23.1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Fix bad example in documentation for dependency groups - by :user:`gaborbernat`. (:issue:`3240`)

v4.23.0 (2024-10-16)
--------------------

Features - 4.23.0
~~~~~~~~~~~~~~~~~
- Add ``NETRC`` to the list of environment variables always passed through. (:issue:`3410`)

Improved Documentation - 4.23.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- replace ``[tool.pyproject]`` and ``[tool.tox.pyproject]`` with ``[tool.tox]`` in config.rst (:issue:`3411`)

v4.22.0 (2024-10-15)
--------------------

Features - 4.22.0
~~~~~~~~~~~~~~~~~
- Implement dependency group support as defined in :pep:`735` - see :ref:`dependency_groups` - by :user:`gaborbernat`. (:issue:`3408`)

v4.21.2 (2024-10-03)
--------------------

Bugfixes - 4.21.2
~~~~~~~~~~~~~~~~~
- Include ``tox.toml`` in sdist archives to fix test failures resulting from its lack.
  - by :user:`mgorny` (:issue:`3389`)

v4.21.1 (2024-10-02)
--------------------

Bugfixes - 4.21.1
~~~~~~~~~~~~~~~~~
- Fix error when using ``requires`` within a TOML configuration file - by :user:`gaborbernat`. (:issue:`3386`)
- Fix error when using ``deps`` within a TOML configuration file - by :user:`gaborbernat`. (:issue:`3387`)
- Multiple fixes for the TOML configuration by :user:`gaborbernat`.:

  - Do not fail when there is an empty command within ``commands``.
  - Allow references for ``set_env`` by accepting list of dictionaries for it.
  - Do not try to be smart about reference unrolling, instead allow the user to control it via the ``extend`` flag,
    available both for ``posargs`` and ``ref`` replacements.
  - The ``ref`` replacements ``raw`` key has been renamed to ``of``. (:issue:`3388`)

v4.21.0 (2024-09-30)
--------------------

Features - 4.21.0
~~~~~~~~~~~~~~~~~
- Native TOML configuration support - by :user:`gaborbernat`. (:issue:`999`)

Improved Documentation - 4.21.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Update Loader docs - by :user:ziima (:issue:`3352`)

v4.20.0 (2024-09-18)
--------------------

Features - 4.20.0
~~~~~~~~~~~~~~~~~
- Separate the list dependencies functionality to a separate abstract class allowing code reuse in plugins (such as
  ``tox-uv``) - by :gaborbernat`. (:issue:`3347`)

v4.19.0 (2024-09-17)
--------------------

Features - 4.19.0
~~~~~~~~~~~~~~~~~
- Support ``pypy-<major>.<minor>`` environment names for PyPy environments - by :user:`gaborbernat`. (:issue:`3346`)

v4.18.1 (2024-09-07)
--------------------

Bugfixes - 4.18.1
~~~~~~~~~~~~~~~~~
- Fix and test the string spec for the ``sys.executable`` interpreter (introduced in :pull:`3325`)
  - by :user:`hroncok` (:issue:`3327`)

Improved Documentation - 4.18.1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Changes the ``tox_env_teardown`` docstring to explain the hook is called after a tox env was teared down. (:issue:`3305`)

v4.18.0 (2024-08-13)
--------------------

Features - 4.18.0
~~~~~~~~~~~~~~~~~
- Suppress spinner in parallel runs in CI - by :user:`ziima`. (:issue:`3318`)

Bugfixes - 4.18.0
~~~~~~~~~~~~~~~~~
- Boost temporary directories cleanup in tests - by :user:`ziima`. (:issue:`3278`)
- Fix absolute base python paths conflicting - by :user:`gaborbernat`. (:issue:`3325`)

v4.17.1 (2024-08-07)
--------------------

Bugfixes - 4.17.1
~~~~~~~~~~~~~~~~~
- Support for running ``-e <major>.<minor>`` has been lost, fixing it - by :user:`gaborbernat`. (:issue:`2849`)
- ``base_python`` now accepts absolute paths to interpreter executable - by :user:`paveldikov`. (:issue:`3191`)

v4.17.0 (2024-08-05)
--------------------

Features - 4.17.0
~~~~~~~~~~~~~~~~~
- Add ``graalpy`` prefix as a supported base python (:issue:`3312`)
- Add :ref:`on_platform` core configuration holding the tox platform and do not install package when exec an environment
  - by :user:`gaborbernat`. (:issue:`3315`)

Bugfixes - 4.17.0
~~~~~~~~~~~~~~~~~
- Add table with default environment variables per OS (:issue:`2753`)

v4.16.0 (2024-07-02)
--------------------

Bugfixes - 4.16.0
~~~~~~~~~~~~~~~~~
- - Add ``windir`` to the default list of Windows ``pass_env`` environment variables. - by :user:`kurtmckee` (:issue:`3302`)

Improved Documentation - 4.16.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- - Fix typo in configuration example and fix broken link to code style guide. - by :user:`srenfo` (:issue:`3297`)

v4.15.1 (2024-06-05)
--------------------

Features - 4.15.1
~~~~~~~~~~~~~~~~~
- Fix ``skip_missing_interpreters`` option for ``package = wheel`` (:issue:`3269`)

Bugfixes - 4.15.1
~~~~~~~~~~~~~~~~~
- Fix section substitution with setenv. (:issue:`3262`)
- Allow ``ConfigSet.add_config`` to receive parameterized generics for ``of_type``. (:issue:`3288`)

v4.15.0 (2024-04-26)
--------------------

Features - 4.15.0
~~~~~~~~~~~~~~~~~
- Add support for multiple appending override options (-x, --override) on command line - by :user:`amitschang`. (:issue:`3261`)
- Add support for inverting exit code success criteria using bang (!) (:issue:`3271`)

Bugfixes - 4.15.0
~~~~~~~~~~~~~~~~~
- Fix issue that the leading character ``c`` was dropped from packages in constraints files - by :user:`jugmac00`. (:issue:`3247`)
- Allow appending to ``deps`` with ``--override testenv.deps+=foo`` - by :user:`stefanor`. (:issue:`3256`)
- Fix non-existing branch ``rewrite`` in the documentation to ``main``. (:issue:`3257`)
- Update test typing for build 1.2.0, which has an explicit ``Distribution`` type - by :user:`stefanor`. (:issue:`3260`)
- Fix broken input parsing for ``--discover`` flag. - by :user:`mimre25` (:issue:`3272`)

Improved Documentation - 4.15.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Rephrase ``--discover`` flag's description to avoid confusion between paths and executables. - by :user:`mimre25` (:issue:`3274`)

v4.14.2 (2024-03-22)
--------------------

Bugfixes - 4.14.2
~~~~~~~~~~~~~~~~~
- Add provision arguments to ToxParser to fix crash when provisioning new tox environment without list-dependencies by :user:`seyidaniels` (:issue:`3190`)

Improved Documentation - 4.14.2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Removed unused line from the ``fresh_subprocess`` documentation. (:issue:`3241`)

v4.14.1 (2024-03-06)
--------------------

Bugfixes - 4.14.1
~~~~~~~~~~~~~~~~~
- Fix crash with fresh subprocess, if the build backend is setuptools automatically enable fresh subprocesses for
  build backend calls - by :user:`gaborbernat`. (:issue:`3235`)

v4.14.0 (2024-03-05)
--------------------

Features - 4.14.0
~~~~~~~~~~~~~~~~~
- Support enabling fresh subprocess for packaging build backends via :ref:`fresh_subprocess` - by :user:`gaborbernat`. (:issue:`3227`)
- Allow plugins attaching additional information to ``--version`` via ``tox_append_version_info`` method in the plugin
  module - by :user:`gaborbernat`. (:issue:`3234`)

v4.13.0 (2024-02-16)
--------------------

Features - 4.13.0
~~~~~~~~~~~~~~~~~
- Extract virtual environment packaging code to its own base class not tied to ``virtualenv`` - by :user:`gaborbernat`. (:issue:`3221`)

Improved Documentation - 4.13.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Documented usage of ``pytest`` with ``tox run-parallel`` - by :user:`faph`. (:issue:`3187`)
- Configuration: state in config directive sections their ini file sections - by :user:`0cjs`. (:issue:`3194`)
- Development: summarize important points experienced developers need to know - by :user:`0cjs`. (:issue:`3197`)

v4.12.1 (2024-01-16)
--------------------

Bugfixes - 4.12.1
~~~~~~~~~~~~~~~~~
- Fixed bug where running with --installpkg and multiple envs could not clean up between tests (:issue:`3165`)

v4.12.0 (2024-01-11)
--------------------

Features - 4.12.0
~~~~~~~~~~~~~~~~~
- Always pass ``FORCE_COLOR`` and ``NO_COLOR`` to the environment (:issue:`3172`)

Bugfixes - 4.12.0
~~~~~~~~~~~~~~~~~
- ``--parallel-no-spinner`` flag now implies ``--parallel`` (:issue:`3158`)

Improved Documentation - 4.12.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- -Fix ``open an issue`` link in development.rst (:issue:`3179`)

v4.11.4 (2023-11-27)
--------------------

Bugfixes - 4.11.4
~~~~~~~~~~~~~~~~~
- Fix terminal size of tox subcommands (fixes ipython, ipdb, prompt_toolkit, ...). (:issue:`2999`)
- Fix ``quickstart`` command from requiring ``root`` positional argument (:issue:`3084`)
- Added 'AppData' to the default passed environment variables on Windows. (:issue:`3151`)

Improved Documentation - 4.11.4
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Fix default value for ``install_command`` - by :user:`hashar`. (:issue:`3126`)
- Fix default value for ``base_python`` - by :user:`rpatterson`. (:issue:`3156`)

v4.11.3 (2023-09-08)
--------------------

Bugfixes - 4.11.3
~~~~~~~~~~~~~~~~~
- Handle ``FileNotFoundError`` when the ``base_python`` interpreter doesn't exist (:issue:`3105`)

Improved Documentation - 4.11.3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Explain how plugins are registered and discovered - by :user:`hashar`. (:issue:`3116`)


v4.11.2 (2023-09-07)
--------------------

Bugfixes - 4.11.2
~~~~~~~~~~~~~~~~~
- Fix bug in ``config.rst`` by removing stray colons left over from (:issue:`3111`) - by :user:`posita`. (:issue:`3118`)
- Provide example to make CLI help more helpful for ``-x`/``--override`` - by :user:`posita`. (:issue:`3119`)

Improved Documentation - 4.11.2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Fix typos discovered by codespell - by :user:`cclauss`. (:issue:`3113`)


v4.11.1 (2023-09-01)
--------------------

Bugfixes - 4.11.1
~~~~~~~~~~~~~~~~~
- Allow passing in multiple overrides using the ``;`` character and fix ``,`` being used as splitting values -
  by :user:`gaborbernat`. (:issue:`3112`)


v4.11.0 (2023-08-29)
--------------------

Features - 4.11.0
~~~~~~~~~~~~~~~~~
- Add support for setting build backend ``config_settings`` in the configuration file - by :user:`gaborbernat`. (:issue:`3090`)


v4.10.0 (2023-08-21)
--------------------

Features - 4.10.0
~~~~~~~~~~~~~~~~~
- Change accepted environment name rule: must be made up of factors defined in configuration or match regex
  ``(pypy|py|cython|)((\d(\.\d+(\.\d+)?)?)|\d+)?``. If an environment name does not match this fail, and if a close match
  found suggest that to the user. (:issue:`3099`)

Bugfixes - 4.10.0
~~~~~~~~~~~~~~~~~
- ``--override foo+=bar`` appending syntax will now work correctly when ``foo`` wasn't defined in ``tox.ini``. (:issue:`3100`)


v4.9.0 (2023-08-16)
-------------------

Features - 4.9.0
~~~~~~~~~~~~~~~~
- Disallow command line environments which are not explicitly specified in the config file - by :user:`tjsmart`. (:issue:`2858`)


v4.8.0 (2023-08-12)
-------------------

Features - 4.8.0
~~~~~~~~~~~~~~~~
- ``--override`` can now take options in the form of ``foo+=bar`` which
  will append ``bar`` to the end of an existing list/dict, rather than
  replacing it. (:issue:`3087`)


v4.7.0 (2023-08-08)
-------------------

Features - 4.7.0
~~~~~~~~~~~~~~~~
- Make ``--hashseed`` default to ``PYTHONHASHSEED``, if defined - by :user:`paravoid`.
  The main motivation for this is to able to set the hash seed when building the
  documentation with ``tox -e docs``, and thus avoid embedding a random value in
  the tox documentation for --help. This caused documentation builds to fail to
  build reproducibly. (:issue:`2942`)

Bugfixes - 4.7.0
~~~~~~~~~~~~~~~~
- Update a regular expression in tests to match the exception message in both Python 3.12 and older. (:issue:`3065`)

Improved Documentation - 4.7.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Fix broken links - by :user:`gaborbernat`. (:issue:`3072`)


v4.6.4 (2023-07-06)
-------------------

Bugfixes - 4.6.4
~~~~~~~~~~~~~~~~
- Fix hang and zombie process on interrupt (CTRL-C). (:issue:`3056`)


v4.6.3 (2023-06-19)
-------------------

Bugfixes - 4.6.3
~~~~~~~~~~~~~~~~
- Ensure that ``get_requires_for_build_wheel`` is called before ``prepare_metadata_for_build_wheel``, and
  ``get_requires_for_build_editable`` is called before ``prepare_metadata_for_build_editable`` - by :user:`abravalheri`. (:issue:`3043`)

Improved Documentation - 4.6.3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Linked environment variable substitutions docs in
  ``set_env`` and ``pass_env`` config docs. (:issue:`3039`)


v4.6.2 (2023-06-16)
-------------------

Bugfixes - 4.6.2
~~~~~~~~~~~~~~~~
- Avoid cache collision between editable wheel build and normal wheel build -- by :user:`f3flight`. (:issue:`3035`)


v4.6.1 (2023-06-15)
-------------------

No significant changes.


v4.6.0 (2023-06-05)
-------------------

Features - 4.6.0
~~~~~~~~~~~~~~~~
- Added ``--list-dependencies`` and ``--no-list-dependencies`` CLI parameters.
  If unspecified, defaults to listing when in CI, but not otherwise. (:issue:`3024`)

Misc - 4.6.0
~~~~~~~~~~~~
- :issue:`3020`


v4.5.1 (2023-05-25)
-------------------

Bugfixes - 4.5.1
~~~~~~~~~~~~~~~~
- Fix ``tox --devenv venv`` invocation without ``-e`` - by :user:`asottile`. (:issue:`2925`)


v4.5.0 (2023-04-24)
-------------------

Features - 4.5.0
~~~~~~~~~~~~~~~~
- When run with verbosity=1, the per-step timing summaries are suppressed at the
  end of the run.  Thanks to :user:`nedbat` at the PyCon 2023 sprints. (:issue:`2891`)

Improved Documentation - 4.5.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add FAQ entry on how to test EOL Python versions by :user:`jugmac00`. (:issue:`2989`)


v4.4.12 (2023-04-13)
--------------------

Bugfixes - 4.4.12
~~~~~~~~~~~~~~~~~
- Avoid race conditions in tests using the ``demo_pkg_inline`` fixture. (:issue:`2985`)


v4.4.11 (2023-04-05)
--------------------

Bugfixes - 4.4.11
~~~~~~~~~~~~~~~~~
- Fixed an issue where a tox plugin couldn't change the value of ``tox_root``. (:issue:`2966`)


v4.4.10 (2023-04-05)
--------------------

Bugfixes - 4.4.10
~~~~~~~~~~~~~~~~~
- Fix issue where ``work_dir`` was not correctly including ``tox_root`` for test runs. (:issue:`2933`)


v4.4.9 (2023-04-05)
-------------------

Bugfixes - 4.4.9
~~~~~~~~~~~~~~~~
- Instead of raising ``UnicodeDecodeError`` when command output includes non-utf-8 bytes,
  ``tox`` will now use ``surrogateescape`` error handling to convert the unrecognized bytes
  to escape sequences according to :pep:`383` - by :user:`masenf`. (:issue:`2969`)

Improved Documentation - 4.4.9
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Document running tox within a Docker container. (:issue:`1035`)
- Added python version 3.11 to ``installation.rst``. (:issue:`2964`)


v4.4.8 (2023-03-26)
-------------------

Bugfixes - 4.4.8
~~~~~~~~~~~~~~~~
- ``tox.ini`` is now included in source distributions in order to make all tests pass. (:issue:`2939`)
- Fix ``--index-url`` and ``--find-links`` being used together in ``requirements.txt`` files. (:issue:`2959`)


v4.4.6 (2023-02-21)
-------------------

Bugfixes - 4.4.6
~~~~~~~~~~~~~~~~
- Plugins are now able to access tox.ini config sections using a custom prefix with the same suffix / name as a tox
  ``testenv`` - by :user:`masenf` (:issue:`2926`)


v4.4.5 (2023-02-07)
-------------------

Bugfixes - 4.4.5
~~~~~~~~~~~~~~~~
- Ignore labels when tox will provision a runtime environment (``.tox``) so that environment configurations which depend
  on provisioned plugins or specific tox versions are not accessed in the outer tox process where the configuration would
  be invalid - by :user:`masenf`. (:issue:`2916`)


v4.4.4 (2023-01-31)
-------------------

Bugfixes - 4.4.4
~~~~~~~~~~~~~~~~
- Forward ``HOME`` by default - by :user:`gschaffner`. (:issue:`2702`)


v4.4.3 (2023-01-30)
-------------------

Bugfixes - 4.4.3
~~~~~~~~~~~~~~~~
- Tox will now expand self-referential extras discovered in package deps to respect local modifications to package
  metadata. This allows a package extra to explicitly depend on another package extra, which previously only worked with
  non-static metadata - by :user:`masenf`. (:issue:`2904`)


v4.4.2 (2023-01-25)
-------------------

Bugfixes - 4.4.2
~~~~~~~~~~~~~~~~
- Allow the user configuration file (default ``<appdir>/tox/config.ini``) to be overridden via the
  ``TOX_USER_CONFIG_FILE`` environment variable. Previously tox was looking at the ``TOX_CONFIG_FILE`` to override the
  user configuration, however that environment variable is already used to override the main configuration - by
  :user:`masenf`. (:issue:`2890`)


v4.4.1 (2023-01-25)
-------------------

Bugfixes - 4.4.1
~~~~~~~~~~~~~~~~
- In tox 4.4.0 ``constrain_package_deps`` was introduced with a default value of ``True``. This has been changed back to
  ``False``, which restores the original behavior of tox 4.3.5 - by :user:`masenf`. (:issue:`2897`)


v4.4.0 (2023-01-25)
-------------------

Features - 4.4.0
~~~~~~~~~~~~~~~~
- Test environments now recognize boolean config keys ``constrain_package_deps`` (default=true) and ``use_frozen_constraints`` (default=false),
  which control how tox generates and applies constraints files when performing ``install_package_deps``.

  If ``constrain_package_deps`` is true (default), then tox will write out ``{env_dir}{/}constraints.txt`` and pass it to
  ``pip`` during ``install_package_deps``. If ``use_frozen_constraints`` is false (default), the constraints will be taken
  from the specifications listed under ``deps`` (and inside any requirements or constraints file referenced in ``deps``).
  Otherwise, ``list_dependencies_command`` (``pip freeze``) is used to enumerate exact package specifications which will
  be written to the constraints file.

  In previous releases, conflicting package dependencies would silently override the ``deps`` named in the configuration,
  resulting in test runs against unexpected dependency versions, particularly when using tox factors to explicitly test
  with different versions of dependencies - by :user:`masenf`. (:issue:`2386`)

Bugfixes - 4.4.0
~~~~~~~~~~~~~~~~
- When parsing command lines, use ``shlex(..., posix=True)``, even on windows platforms, since non-POSIX mode does not
  handle escape characters and quoting like a shell would. This improves cross-platform configurations without hacks or
  esoteric quoting.

  To make this transition easier, on Windows, the backslash path separator will not treated as an escape character unless
  it precedes a quote, whitespace, or another backslash character. This allows paths to mostly be written in single or
  double backslash style.

  Note that **double-backslash will no longer be escaped to a single backslash in substitutions**, instead the double
  backslash will be consumed as part of command splitting, on either posix or windows platforms.

  In some instances superfluous double or single quote characters may be stripped from arg arrays in ways that do not
  occur in the default windows ``cmd.exe`` shell - by :user:`masenf`. (:issue:`2635`)

Improved Documentation - 4.4.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add information when command from ``list_dependencies_command`` configuration option is used. (:issue:`2883`)


v4.3.5 (2023-01-18)
-------------------

Bugfixes - 4.3.5
~~~~~~~~~~~~~~~~
- When building a ``wheel`` or ``editable`` package with a PEP 517 backend, no
  longer pass an empty ``metadata_directory`` to the backend ``build_wheel`` or
  ``build_editable`` endpoint.

  Some backends, such as PDM and poetry, will not generate package metadata in
  the presence of a ``metadata_directory``, even if it is empty.

  Prior to this change, attempting to install a wheel created by tox using PDM or
  poetry would return an error like "There is no item named
  'my-package.0.1.dist-info/WHEEL' in the archive" - by :user:`masenf`. (:issue:`2880`)


v4.3.4 (2023-01-17)
-------------------

Bugfixes - 4.3.4
~~~~~~~~~~~~~~~~
- When executing via the provisioning environment (``.tox`` by default), run
  ``tox`` in working directory of the parent process.

  Prior to this change (from tox 4.0.0), the provisioned ``tox`` would execute with
  ``{tox_root}`` as the working directory, which breaks when a relative path is
  passed to ``-c`` or ``--conf`` and ``tox`` is executed in a working directory
  other than ``{tox_root}`` - by :user:`masenf`. (:issue:`2876`)

Misc - 4.3.4
~~~~~~~~~~~~
- :issue:`2878`


v4.3.3 (2023-01-16)
-------------------

Bugfixes - 4.3.3
~~~~~~~~~~~~~~~~
- The provision environment (``.tox``) will never inherit from ``testenv``.
  During provisioning, other test environments are not processed, allowing the
  use of keys and values that may be registered by later tox version or
  provisioned plugins - by :user:`masenf`. (:issue:`2862`)


v4.3.2 (2023-01-16)
-------------------

Bugfixes - 4.3.2
~~~~~~~~~~~~~~~~
- Fix regression introduced in 4.3.0 which occurred when a substitution expression
  for an environment variable that had previously been substituted appears in the
  ini file after a substitution expression for a different environment variable.
  This situation erroneously resulted in an exception about "circular chain
  between set" of those variables - by :user:`masenf`. (:issue:`2869`)


v4.3.1 (2023-01-15)
-------------------

Bugfixes - 4.3.1
~~~~~~~~~~~~~~~~
- Fix regression introduced in 4.3.0 by expanding substitution expressions
  (``{...}``) that result from a previous subsitution's replacement value (up to
  100 times). Note that recursive expansion is strictly depth-first; no
  replacement value will ever affect adjacent characters nor will expansion ever
  occur over the result of more than one replacement - by :user:`masenf`. (:issue:`2863`)


v4.3.0 (2023-01-15)
-------------------

Features - 4.3.0
~~~~~~~~~~~~~~~~
- Rewrite substitution replacement parser - by :user:`masenf`

  * ``\`` acts as a proper escape for ``\`` in ini-style substitutions
  * The resulting value of a substitution is no longer reprocessed in the context
    of the broader string. (Prior to this change, ini-values were repeatedly re-substituted until
    the expression no longer had modifications)
  * Migrate and update "Substitutions" section of Configuration page from v3 docs.
  * ``find_replace_part`` is removed from ``tox.config.loader.ini.replace``
  * New names exported from ``tox.config.loader.ini.replace``:
      * ``find_replace_expr``
      * ``MatchArg``
      * ``MatchError``
      * ``MatchExpression``
      * Note: the API for ``replace`` itself is unchanged. (:issue:`2732`)
- Improved documentation for factors and test env names - by :user:`stephenfin`. (:issue:`2852`)


v4.2.8 (2023-01-11)
-------------------

Bugfixes - 4.2.8
~~~~~~~~~~~~~~~~
- Allow using package names with env markers for pip's ``--no-binary`` and ``--only-binary`` options - by :user:`q0w`. (:issue:`2814`)


v4.2.7 (2023-01-11)
-------------------

Bugfixes - 4.2.7
~~~~~~~~~~~~~~~~
- A testenv with multiple factors, one of which conflicts with a ``base_python`` setting in ``tox.ini``, will now use the
  correct Python interpreter version - by :user:`stephenfin`. (:issue:`2838`)
- Explicitly list ``wheel`` as requirement for the tests, as some of the tests error without it. (:issue:`2843`)
- tox has reverted support for Python factors that include PATCH release info (e.g. ``py3.10.1``), build architecture
  (e.g. ``pypy3-64``) or do not define a ``py`` prefix or other supported prefix (e.g. ``3.10``). These complex factors
  were initially supported with the release of tox 4.0 but has proven complicated to support. Instead, the simple factors
  supported by tox 3 e.g. (``py310``, ``pypy3``) or period-separated equivalent (``py3.10``) introduced in tox 4 should be
  used. Users who wish to specify more specific Python version information should configure the :ref:`base_python` setting
  - by :user:`stephenfin`. (:issue:`2848`)


v4.2.6 (2023-01-06)
-------------------

Bugfixes - 4.2.6
~~~~~~~~~~~~~~~~
- Handle properly pip ``--no-binary`` / ``--only-binary`` options in requirements.txt format files. (:issue:`2814`)


v4.2.5 (2023-01-06)
-------------------

Bugfixes - 4.2.5
~~~~~~~~~~~~~~~~
- The combination of ``usedevelop = true`` and ``--skip-missing-interpreters=false`` will no longer fail for environments
  that were *not* invoked - by :user:`stephenfin`. (:issue:`2811`)
- Fix an attribute error when ``use_develop = true`` is set and an unsupported interpreter version is requested - by
  :user:`stephenfin`. (:issue:`2826`)
- tox returns a non-zero error code if all envs are skipped. It will now correctly do this if only a single env was
  requested and this was skipped - by :user:`stephenfin`. (:issue:`2827`)


v4.2.4 (2023-01-05)
-------------------

Bugfixes - 4.2.4
~~~~~~~~~~~~~~~~
- Setting ``[testenv] basepython = python3`` will no longer override the Python interpreter version requested by a factor,
  such as ``py311`` - by :user:`stephenfin`. (:issue:`2754`)
- Also accept tab after colon before factor filter expansion - by :user:`pdecat`. (:issue:`2823`)


v4.2.3 (2023-01-04)
-------------------

Bugfixes - 4.2.3
~~~~~~~~~~~~~~~~
- ``devenv`` does not respect the specified path when the package is a wheel file - by :user:`gaborbernat`. (:issue:`2815`)
- Require space after colon before factor filter expansion, unless it is the last character of the line - by :user:`pdecat`. (:issue:`2822`)


v4.2.2 (2023-01-04)
-------------------

Bugfixes - 4.2.2
~~~~~~~~~~~~~~~~
- Add ``CC``, ``CFLAGS``, ``CCSHARED``, ``CXX``, ``CPPFLAGS``, ``LDFLAGS``, ``PKG_CONFIG`` and ``PKG_CONFIG_SYSROOT_DIR``
  to the default passed through environment variables list as these are needed for building various C-extensions
  - by :user:`gaborbernat`. (:issue:`2818`)


v4.2.1 (2023-01-03)
-------------------

Bugfixes - 4.2.1
~~~~~~~~~~~~~~~~
- Fix extracting extras from markers with more than 2 extras in an or chain - by :user:`dconathan`. (:issue:`2791`)


v4.2.0 (2023-01-03)
-------------------

Features - 4.2.0
~~~~~~~~~~~~~~~~
- Packaging environments now inherit from the ``pkgenv`` section, allowing to set all your packaging options in one place,
  and support the ``deps`` key to set additional dependencies that will be installed after ``pyproject.toml`` static
  ``requires`` but before backends dynamic requires - by :user:`gaborbernat`. (:issue:`2543`)

Improved Documentation - 4.2.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Document breaking changes with tox 4 and packaging environments - by :user:`gaborbernat`. (:issue:`2543`)
- Document how to handle environments whose names match ``tox`` subcommands - by :user:`sirosen`. (:issue:`2728`)


v4.1.3 (2023-01-02)
-------------------

Bugfixes - 4.1.3
~~~~~~~~~~~~~~~~
- Reuse package_env with ``--installpkg`` - by :user:`q0w`. (:issue:`2442`)
- Fail more gracefully when pip :ref:`install_command` is empty - by :user:`jayaddison`. (:issue:`2695`)

Improved Documentation - 4.1.3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add breaking-change documentation for empty ``install_command`` values - by :user:`jayaddison`. (:issue:`2695`)

Misc - 4.1.3
~~~~~~~~~~~~
- :issue:`2796`, :issue:`2797`


v4.1.2 (2022-12-30)
-------------------

Bugfixes - 4.1.2
~~~~~~~~~~~~~~~~
- Fix ``--skip-missing-interpreters`` behavior - by :user:`q0w`. (:issue:`2649`)
- Restore tox 3 behavior of showing the output of pip freeze, however now only active when running inside a CI
  environment - by :user:`gaborbernat`. (:issue:`2685`)
- Fix extracting extras from markers with many extras - by :user:`q0w`. (:issue:`2791`)


v4.1.1 (2022-12-29)
-------------------

Bugfixes - 4.1.1
~~~~~~~~~~~~~~~~
- Fix logging error with emoji in git branch name. (:issue:`2768`)

Improved Documentation - 4.1.1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add faq entry about reuse of environments - by :user:`jugmac00`. (:issue:`2788`)


v4.1.0 (2022-12-29)
-------------------

Features - 4.1.0
~~~~~~~~~~~~~~~~
- ``-f`` can be used multiple times and on hyphenated factors (e.g. ``-f py311-django -f py39``) - by :user:`sirosen`. (:issue:`2766`)

Improved Documentation - 4.1.0
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Fix a grammatical typo in docs/user_guide.rst. (:issue:`2787`)


v4.0.19 (2022-12-28)
--------------------

Bugfixes - 4.0.19
~~~~~~~~~~~~~~~~~
- Create temp_dir if not exists - by :user:`q0w`. (:issue:`2770`)


v4.0.18 (2022-12-26)
--------------------

Bugfixes - 4.0.18
~~~~~~~~~~~~~~~~~
- Strip leading and trailing whitespace when parsing elements in requirement files - by :user:`gaborbernat`. (:issue:`2773`)


v4.0.17 (2022-12-25)
--------------------

Features - 4.0.17
~~~~~~~~~~~~~~~~~
- Suppress a report output when verbosity = 0. (:issue:`2697`)

Bugfixes - 4.0.17
~~~~~~~~~~~~~~~~~
- Fix ``--sdistonly`` behavior. (:issue:`2653`)
- Override toxworkdir with --workdir. (:issue:`2654`)


v4.0.16 (2022-12-20)
--------------------

Bugfixes - 4.0.16
~~~~~~~~~~~~~~~~~
- Fix :ref:`change_dir` is relative to current working directory rather than to the :ref:`tox_root` when using the ``-c``
  argument to locate the ``tox.ini`` file - by :user:`gaborbernat`. (:issue:`2619`)


v4.0.15 (2022-12-19)
--------------------

Bugfixes - 4.0.15
~~~~~~~~~~~~~~~~~
- Fix tox auto-provisioning not working and relax :ref:`min_version` default from ``4.0`` to no version constraint
  - by :user:`gaborbernat`. (:issue:`2634`)
- Fix assertion in ``test_result_json_sequential`` when interpreter ``_base_executable`` is a hardlink (macOS homebrew)
  - by :user:`masenf`. (:issue:`2720`)
- Complex negative factor filters not working  - by :user:`gaborbernat`. (:issue:`2747`)


v4.0.14 (2022-12-18)
--------------------

Bugfixes - 4.0.14
~~~~~~~~~~~~~~~~~
- Do not include non test environment sections or factor filters in INI configuration to factor discovery - by
  :user:`gaborbernat`. (:issue:`2746`)


v4.0.13 (2022-12-17)
--------------------

Bugfixes - 4.0.13
~~~~~~~~~~~~~~~~~
- A plain section in INI configuration matching a tox environment name shadowed the laters configuration - by
  :user:`gaborbernat`. (:issue:`2636`)
- Fix space not accepted in factor filter expression - by :user:`gaborbernat`. (:issue:`2718`)


v4.0.12 (2022-12-16)
--------------------

Bugfixes - 4.0.12
~~~~~~~~~~~~~~~~~
- If tox is running in a tty, allocate a pty (pseudo terminal) for commands
  and copy termios attributes to show colors and improve interactive use - by :user:`masenf`. (:issue:`1773`)
- Fix python hash seed not being set - by :user:`gaborbernat`. (:issue:`2645`)
- Fix legacy CLI flags ``--pre``, ``--force-deps``, ``--sitepackages`` and ``--alwayscopy`` not working, and mark them
  as deprecated - by :user:`gaborbernat`. (:issue:`2690`)

Improved Documentation - 4.0.12
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Document user level config. (:issue:`2633`)


v4.0.11 (2022-12-14)
--------------------

Features - 4.0.11
~~~~~~~~~~~~~~~~~
- Modified handling of ``NO_COLOR`` environment variable, consistent with
  `de facto conventions <https://no-color.org>`_: any non-empty string will enable ``NO_COLOR`` (disable colorized
  output); no ``NO_COLOR`` variable or ``NO_COLOR`` with an empty string will disable ``NO_COLOR`` (enable colorized
  output) - by :user:`ptmcg`. (:issue:`2719`)

Bugfixes - 4.0.11
~~~~~~~~~~~~~~~~~
- ``TOX_SKIP_ENV`` environment variable now works again, and can also be set via the CLI argument ``--skip-env``
  for any command where ``-e`` can be set - by :user:`mgedmin`. (:issue:`2698`)
- ``tox config`` should only show :ref:`env_list` arguments by default instead of ``ALL`` - by :user:`gaborbernat`. (:issue:`2726`)


v4.0.10 (2022-12-14)
--------------------

Features - 4.0.10
~~~~~~~~~~~~~~~~~
- Add ``py_dot_ver`` and ``py_impl`` constants to environments to show the current Python implementation and dot version
  (e.g. ``3.11``) for the current environment. These can be also used as substitutions in ``tox.ini`` - by
  :user:`gaborbernat`. (:issue:`2640`)

Bugfixes - 4.0.10
~~~~~~~~~~~~~~~~~
- ``--help`` now reports the default verbosity level (which is WARNING) correctly. (:issue:`2707`)


v4.0.9 (2022-12-13)
-------------------

Features - 4.0.9
~~~~~~~~~~~~~~~~
- Add :meth:`tox_on_install <tox.plugin.spec.tox_on_install>` and
  :meth:`tox_env_teardown <tox.plugin.spec.tox_env_teardown>` plugin hooks - by :user:`gaborbernat`. (:issue:`2687`)
- Add ``PKG_CONFIG_PATH`` to the default pass through environment list for python tox environments -
  by :user:`gaborbernat`. (:issue:`2700`)


v4.0.8 (2022-12-11)
-------------------

Bugfixes - 4.0.8
~~~~~~~~~~~~~~~~
- Fix multiple substitution on factor filtering in ``tox.ini`` when multiple factor filters match
  - by :user:`gaborbernat`. (:issue:`2650`)
- Fix regression in ``requirements.txt`` parsing - by :user:`gaborbernat`. (:issue:`2682`)


v4.0.7 (2022-12-11)
-------------------

Bugfixes - 4.0.7
~~~~~~~~~~~~~~~~
- Support for ``--no-deps`` flag within the :ref:`deps` - by :user:`gaborbernat`. (:issue:`2674`)


v4.0.6 (2022-12-10)
-------------------

Features - 4.0.6
~~~~~~~~~~~~~~~~
- Fail on :ref:`pass_env`/:ref:`passenv` entries containing whitespace - by :user:`ericzolf`. (:issue:`2658`)


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
   `legacy branch documentation <https://tox.wiki/en/legacy/changelog.html>`_.
