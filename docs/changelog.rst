###########
 Changelog
###########

.. towncrier-draft-entries:: Unreleased

.. towncrier release notes start

.. _release-4-67-1:

*********************
 4.67.1 (2026-10-18)
*********************

.. _release-4-67-1-fixed:

Fixed
-----

- Preserve ignore (``-``) and invert (``!``) exit code prefixes on commands when referenced via TOML ``{ replace =
  "ref", ... }``. (:issue:`4169`)
- Installing from a ``pylock.toml`` with no :ref:`dependency_groups` selected now uses the lock file's
  ``default-groups``, as :PEP:`751` specifies. Previously packages marked ``'default' in dependency_groups`` (as written
  by ``pdm export -f pylock``) were skipped - by :user:`pcbeingused333`. (:issue:`4173`)
- A positional ``{factor:N}`` label in an ``env_base`` now resolves against that table's own ``factors``, so with
  several ``env_base`` tables or an ``env_list`` ``product`` it no longer expands to an empty string. (:issue:`4174`)

.. _release-4-67-0:

*********************
 4.67.0 (2026-10-17)
*********************

.. _release-4-67-0-added:

Added
-----

- Allow opting in to tox substitutions within TOML positional arguments with ``substitute = true``. (:issue:`4165`)

.. _release-4-67-0-fixed:

Fixed
-----

- Keep capturing the output of the packaging backend with ``--no-capture``, so ``tox --no-capture`` no longer hangs at
  ``started backend`` while waiting for the backend's reply. (:issue:`4163`)
- A leading UTF-8 byte order mark in ``tox.ini``, ``setup.cfg``, ``tox.toml`` or a TOML ``pyproject.toml`` no longer
  stops the configuration from loading - editors on Windows may add one. (:issue:`4166`)
- ``tox --no-provision <command>`` no longer treats the command as the JSON output path: a global option placed before a
  subcommand now keeps it, so ``tox --no-provision list`` lists the environments instead of writing a file named
  ``list``. (:issue:`4168`)

.. _release-4-67-0-documentation:

Documentation
-------------

- Link overridden argparse methods and logging.Handler.name in the plugin API reference. (:issue:`4170`)

.. _release-4-66-0:

*********************
 4.66.0 (2026-10-16)
*********************

.. _release-4-66-0-added:

Added
-----

- ``set_env`` environment files accept ``export KEY=value`` lines, setting ``KEY`` - by :user:`RavSinghChandan`.
  (:issue:`4161`)

.. _release-4-66-0-fixed:

Fixed
-----

- Remember a failed interpreter lookup for a virtualenv environment instead of repeating the full ``PATH`` scan for
  every setting that needs it, so ``tox config`` and ``tox run`` on configurations listing interpreters that are not
  installed are faster. (:issue:`4162`)

.. _release-4-65-6:

*********************
 4.65.6 (2026-10-15)
*********************

.. _release-4-65-6-fixed:

Fixed
-----

- Preserve literal single and double quotes in Windows command arguments. (:issue:`4159`)
- Keep quotes in positional arguments on Windows, so ``tox -- "'x'"`` passes ``'x'`` to the command as on Linux
  (:issue:`4160`)

.. _release-4-65-5:

*********************
 4.65.5 (2026-10-14)
*********************

.. _release-4-65-5-fixed:

Fixed
-----

- Keep braces that are not a substitution in TOML configurations, as INI does, so ``{}`` in ``find -exec`` or a dict
  literal in ``python -c`` reaches the command intact (:issue:`4150`)

.. _release-4-65-4:

*********************
 4.65.4 (2026-10-12)
*********************

.. _release-4-65-4-documentation:

Documentation
-------------

- Clarify how ``TOX_`` environment variables set CLI option defaults and how ``TOX_OVERRIDE`` changes configuration
  values. (:issue:`4146`)

.. _release-4-65-3:

*********************
 4.65.3 (2026-10-11)
*********************

.. _release-4-65-3-fixed:

Fixed
-----

- Allow ``--skip-env`` with ``-e``, ``-m``, and ``-f`` so it filters the selected environments (:issue:`4143`)

.. _release-4-65-2:

*********************
 4.65.2 (2026-10-10)
*********************

.. _release-4-65-2-fixed:

Fixed
-----

- A ``dependency_groups`` run whose package root has no ``pyproject.toml`` now fails with the path it looked at, instead
  of installing none of the requested groups and reporting success - by :user:`feiiiiii5`. (:issue:`4142`)

.. _release-4-65-1:

*********************
 4.65.1 (2026-10-10)
*********************

.. _release-4-65-1-fixed:

Fixed
-----

- tox removes read-only files on Windows when it empties an environment's ``tmp`` or log directory, or the whole
  environment on recreate - by :user:`SulimanAbdulrazzaq`.

  - A read-only file in the directory itself used to stop every later run with ``internal error``.
  - A read-only file in a sub-directory used to stay behind without a warning. (:issue:`4138`)

.. _release-4-65-1-packaging:

Packaging
---------

- Use Python 3.15 for development and automation. (:issue:`4139`)
- Include the plugin documentation in source distributions so downstream packagers can run the plugin example tests.
  (:issue:`4140`)

.. _release-4-65-0:

*********************
 4.65.0 (2026-10-09)
*********************

.. _release-4-65-0-added:

Added
-----

- Bump the default maximum CPython minor version to 3.15 in generative environment lists. (:issue:`4136`)

.. _release-4-65-0-fixed:

Fixed
-----

- ``--result-json`` and ``tox config -o`` create the missing parent directory of the output file instead of crashing -
  by :user:`SulimanAbdulrazzaq`. (:issue:`4126`)
- A ``set_env`` env file that is a directory or not UTF-8 fails the environment with a configuration error instead of a
  traceback, and a leading UTF-8 byte order mark no longer ends up in the first key - by :user:`SulimanAbdulrazzaq`.
  (:issue:`4127`)
- A reused environment with ``commands = []`` clears ``env_log_dir`` at the start of the run instead of keeping logs
  from the previous run - by :user:`glaziermag`. (:issue:`4130`)

.. _release-4-65-0-documentation:

Documentation
-------------

- Drop ``@impl`` from the ``tox_append_version_info`` plugin doc examples, since it made tox skip the inline plugin - by
  :user:`Rodrigo-Palma`. (:issue:`4135`)

.. _release-4-64-10:

**********************
 4.64.10 (2026-10-08)
**********************

.. _release-4-64-10-fixed:

Fixed
-----

- Report an invalid configuration value as a one-line error naming the environment and key instead of a traceback,
  including ``-x`` overrides and values set by plugins - by :user:`hfycium`. (:issue:`4118`)
- A command prefixed with ``!`` that exits with ``0`` now fails the environment with exit code ``1``; before, tox
  reported it as a success - by :user:`feiiiiii5`. (:issue:`4119`)
- Recreating an environment or clearing its temporary and log directories removes symlinks to directories, leaving their
  targets intact - by :user:`gaborbernat`. (:issue:`4121`)
- A command prefixed with ``!`` that cannot start, such as a missing executable, now fails the environment instead of
  passing - by :user:`feiiiiii5`. (:issue:`4125`)

.. _release-4-64-9:

*********************
 4.64.9 (2026-10-05)
*********************

.. _release-4-64-9-fixed:

Fixed
-----

- Resolve substitutions and ``file|`` entries in :ref:`set_env` overrides passed through ``-x`` or ``TOX_OVERRIDE``.
  Appended blocks replace inherited values while preserving explicit keys in the same or later overrides. Preserve these
  rules through section references, including native TOML arrays with ``extend = true``. Resolve env-file selectors and
  values in the consuming environment. Prevent included values from overriding tox's own variables - by
  :user:`Rodrigo-Palma`. (:issue:`4116`)

.. _release-4-64-8:

*********************
 4.64.8 (2026-10-03)
*********************

.. _release-4-64-8-fixed:

Fixed
-----

- tox combines ``--no-binary`` and ``--only-binary`` across the lines of ``deps`` and of requirements files the way pip
  does, where the last line used to replace the earlier ones. With ``--only-binary :all:`` and a ``--no-binary``
  exception, tox passes ``--only-binary`` to pip first, so pip keeps the exception. ``tox config`` shows the merged
  values tox passes to pip - by :user:`SulimanAbdulrazzaq`. (:issue:`4110`)
- ``tox config`` shows ``deps`` with every global option merged the way tox passes it to pip, a later ``-i`` replacing
  an earlier one and repeated flags shown once, and reports the error ``tox run`` would raise for invalid ``deps``.
  ``constraints`` shows the configured files instead of the path of ``tox.ini``, and a comment line in ``constraints``
  no longer fails the run. ``deps`` that give pip nothing to install no longer conflict with ``pylock``. ``set_env``
  includes ``PIP_USER``, ``TOX_ENV_DIR``, ``TOX_ENV_NAME``, ``TOX_WORK_DIR`` and ``VIRTUAL_ENV``, the values tox sets
  for commands - by :user:`gaborbernat`. (:issue:`4111`)
- A TOML ``ref`` to another environment's ``deps``, ``constraints`` or ``commands`` works in ``tox config`` and ``tox
  run``. It used to fail with ``'PythonDeps' object is not iterable`` or ``Command(args=[...]) is not list`` - by
  :user:`gaborbernat`. (:issue:`4112`)
- In INI ``commands``, ``commands_pre`` and ``commands_post``, a reference such as ``pip install {[testenv:x]deps}``
  that shares its line with other text joins the referenced lines into that one command as arguments, as in tox 3. tox
  used to run each referenced line after the first as a separate command. A reference alone on its line still expands to
  one command per referenced line. This changes ``echo {[testenv:x]commands}``, which now runs one ``echo`` with every
  referenced command as its arguments - by :user:`gaborbernat`. (:issue:`4113`)
- The JSON schema described :ref:`requires` with the text of :ref:`provision_tox_env`, so editors showed the wrong hover
  for it - by :user:`gaborbernat`. (:issue:`4115`)

.. _release-4-64-8-documentation:

Documentation
-------------

- The configuration reference listed wrong defaults for :ref:`args_are_paths` (``True``), :ref:`pkg_dir`
  (``{env_dir}/dist``), :ref:`skip_missing_interpreters` (``False``), :ref:`min_version` (unset) and :ref:`requires`
  (``tox``) - by :user:`Rodrigo-Palma`. (:issue:`4114`)

.. _release-4-64-7:

*********************
 4.64.7 (2026-10-01)
*********************

.. _release-4-64-7-fixed:

Fixed
-----

- ``tox man`` suggests ``~/.profile`` instead of ``~/.zshrc`` when the shell is not fish, bash, zsh, csh or tcsh, for
  example ``sh``, ``ksh`` or an unset ``SHELL`` - by :user:`Rodrigo-Palma`.

  - tox picks the shell from the executable name, so ``/home/zshuser/bin/bash`` gets ``~/.bashrc``.
  - Outside fish, csh and tcsh, the reload hint reads ``. <file>`` instead of ``source <file>``, since ``dash`` has no
    ``source``.
  - The fish line keeps the default man path when ``MANPATH`` was unset, instead of hiding every other man page.
  - csh and tcsh get a ``setenv`` line for ``~/.tcshrc`` or ``~/.cshrc`` instead of an ``export`` line for
    ``~/.profile``. (:issue:`4109`)

.. _release-4-64-6:

*********************
 4.64.6 (2026-10-01)
*********************

.. _release-4-64-6-fixed:

Fixed
-----

- ``tox -e`` and ``TOXENV`` accept every interpreter name that picks a ``base_python`` for an environment the
  configuration does not declare - by :user:`breken-ai`.

  - ``cpython313``, ``cpython-3.13``, ``graalpy311``, ``jython2.7``, ``rustpython3`` and ``ironpython3`` select that
    interpreter instead of failing with "provided environments not found".
  - The ``d`` debug-build suffix works too, for example ``py313d``.
  - ``cython313`` now fails as an unknown environment; it used to run on the Python that tox runs under. (:issue:`4106`)

- A ``set_env`` block pulled in with ``{[section]set_env}`` now applies a PEP-508 marker only to the value it came with,
  as the inline and TOML forms already do - by :user:`feiiiiii5`. A false marker on an earlier line no longer hides a
  value that the inheriting environment, a later unconditional line or an environment file supplies. (:issue:`4107`)
- ``set_env`` values resolve when tox reads them, so ``{env:KEY}`` sees the keys a block pulls in with
  ``{[section]set_env}``, and a ``{ replace = "env" }`` table sees the keys next to it - by :user:`gaborbernat`, found
  by :user:`breken-ai`. Configurations that see a difference:

  - A value pulled in from another section that refers to a key of the same block now gets the block's value instead of
    the host variable.
  - A pulled-in line that refers to its own key, such as ``PYTHONHASHSEED = {env:PYTHONHASHSEED:0}``, reads the host
    variable or its default, as the same line written in place does. It used to read the value tox sets.
  - A key written in an INI ``set_env`` wins over the same key pulled in from another section, and a later pulled-in
    section wins over an earlier one, at every nesting level. A nested section could override the section that included
    it before.
  - ``tox config`` shows the keys of every pulled-in section that ``tox run`` sets.
  - A section that pulls itself in, a TOML ``ref`` to itself, and values that refer to each other fail the environment
    with the cycle. They used to fail with a traceback or "could not find python interpreter", and values that referred
    to each other inside a pulled-in section read the host variables without a warning. (:issue:`4108`)

.. _release-4-64-5:

*********************
 4.64.5 (2026-09-29)
*********************

.. _release-4-64-5-fixed:

Fixed
-----

- An invalid ``platform`` regular expression now fails the environment with a one-line error instead of a traceback,
  also for the provisioning environment - by :user:`00200200`. (:issue:`4103`)

.. _release-4-64-4:

*********************
 4.64.4 (2026-09-27)
*********************

.. _release-4-64-4-fixed:

Fixed
-----

- Pass ``--pre`` once, before the packages, in the default ``install_command`` with :ref:`pip_pre` set to ``true``.
  (:issue:`4097`)
- Fix list conversion for command line defaults from environment variables and user configuration files. For example,
  ``TOX_LABELS=old;new`` selects environments labeled ``old`` or ``new``, and ``TOX_LIST_KEYS_ONLY=env_name;deps``
  selects both configuration keys. Support list-valued options without an explicit default or element type, including
  append actions. (:issue:`4098`)

.. _release-4-64-3:

*********************
 4.64.3 (2026-09-26)
*********************

.. _release-4-64-3-fixed:

Fixed
-----

- A ``set_env`` written as a list of tables in TOML now keeps every ``file`` entry and honors the order of the entries,
  so merging one environment's ``set_env`` into another no longer drops the environment file it referenced
  (:issue:`4093`) - by :user:`Rodrigo-Palma`.

  - Each ``{ file = "..." }`` entry is read; previously only the last one survived, because the entries were merged into
    a single table first and a table cannot hold the key twice.
  - A variable set after a ``file`` entry wins over the value the file provides, matching the ``file|`` form in INI;
    previously a repeated variable was pulled back to its first position, letting the file override it.
  - A later entry that sets a variable without a marker clears the marker an earlier entry gave it, again matching the
    INI form. (:issue:`4093`)

- Create the package build environment ``change_dir`` directory before running the build commands, as the documentation
  already promises. (:issue:`4095`)

.. _release-4-64-2:

*********************
 4.64.2 (2026-09-24)
*********************

.. _release-4-64-2-fixed:

Fixed
-----

- A tox environment with ``env_dir = "{tox_root}/.venv"`` no longer crashes with ``FileExistsError`` after another
  environment ran (:issue:`4090`) - by :user:`gaborbernat`.

  - With ``venv_redirect`` unset, the new default, tox writes the redirect file unless a tox environment lives at
    ``.venv``; with ``true``, tox fails the run with an error naming that environment.
  - tox deletes a redirect file it wrote where an environment should live, and fails the environment with an error
    naming any other file there. (:issue:`4091`)

- The :PEP:`832` ``.venv`` redirect file now names a deliberate development environment - by :user:`gaborbernat`.

  - tox picks :ref:`venv_redirect_env`, else an environment named ``dev``, else the first that installs the project in
    development mode, and writes nothing without one, so a project that uses tox for tests alone gets no file.
  - ``tox devenv`` points the redirect at the environment it creates, and later runs leave it in place.
  - tox tells virtualenv to write no redirect file of its own beside the environments it builds. (:issue:`4092`)

.. _release-4-64-1:

*********************
 4.64.1 (2026-09-24)
*********************

.. _release-4-64-1-fixed:

Fixed
-----

- Apply ``-x``/``--override`` and ``TOX_OVERRIDE`` values that target a section the configuration file does not define,
  such as ``tox.skip_missing_interpreters`` on a ``tox.ini`` without a ``[tox]`` section, instead of dropping them - by
  :user:`gaborbernat`. (:issue:`4089`)

.. _release-4-64-0:

*********************
 4.64.0 (2026-09-24)
*********************

.. _release-4-64-0-added:

Added
-----

- Point a :PEP:`832` ``.venv`` redirect file at a tox environment after each run, so editors such as VS Code or PyCharm
  pick it as the project interpreter instead of asking you for a path under ``.tox`` - by :user:`gaborbernat`.

  - tox picks an environment named ``dev``, then one installing the project in development mode, then the first of
    :ref:`env_list`; set :ref:`venv_redirect_env` to choose another.
  - tox leaves a ``.venv`` directory alone, and a redirect file pointing outside its environments.
  - tox removes the redirect while it recreates the target and writes it back once the run ends.
  - Set ``venv_redirect`` to ``false`` to opt out.
  - The feature is provisional while :PEP:`832` is a draft: a minor or patch release may change it in backward
    incompatible ways to follow the PEP. (:issue:`4013`)

.. _release-4-64-0-fixed:

Fixed
-----

- The user configuration file is now read as UTF-8 instead of the platform's locale encoding, so a config holding
  non-ASCII values is no longer silently discarded on Windows - by :user:`MohammedAlkindi`. (:issue:`4086`)

.. _release-4-64-0-documentation:

Documentation
-------------

- Fix the invalid table header in the TOML string substitution example. (:issue:`4081`)

.. _release-4-63-0:

*********************
 4.63.0 (2026-09-19)
*********************

.. _release-4-63-0-added:

Added
-----

- Plugins and test helpers can use ``tox.execute.api.FinishedExecuteStatus`` to report a fixed exit code for a command
  that already finished or never started - by :user:`gaborbernat`. (:issue:`4080`)

.. _release-4-63-0-fixed:

Fixed
-----

- Interrupting a parallel run with Ctrl-C no longer loses the log lines about stopping the package environment, which
  could appear or vanish depending on thread timing - by :user:`gaborbernat`. (:issue:`4079`)
- Optional dependencies declared in ``pyproject.toml`` under a name that is not normalized, such as ``Foo_Bar``, are now
  installed when requested as ``extras = foo-bar`` while tox installs a package's dependencies - by :user:`gaborbernat`.
  (:issue:`4080`)

.. _release-4-62-1:

*********************
 4.62.1 (2026-09-19)
*********************

.. _release-4-62-1-fixed:

Fixed
-----

- Clear obsolete markers when unconditional ``set_env`` values override conditional entries, including environment
  files. (:issue:`4076`)

.. _release-4-62-0:

*********************
 4.62.0 (2026-09-19)
*********************

.. _release-4-62-0-added:

Added
-----

- Plugins can read a configuration value that may be unset through ``ConfigSet.get_optional``, which verifies the value
  against its declared type and returns ``None`` when it is not set - by :user:`gaborbernat`. (:issue:`4075`)

.. _release-4-62-0-fixed:

Fixed
-----

- Setting ``TOX_FACTOR_<label>`` to an empty value now resolves ``{factor:<label>}`` to an empty string instead of being
  ignored - by :user:`gaborbernat`. (:issue:`4073`)

.. _release-4-61-5:

*********************
 4.61.5 (2026-09-17)
*********************

.. _release-4-61-5-fixed:

Fixed
-----

- An empty ``set_env`` list in TOML no longer fails to load; like an empty table, it clears inherited variables - by
  :user:`yuefdev`. (:issue:`4065`)
- A TOML factor range now rejects ``true`` or ``false`` as ``start`` or ``stop`` instead of reading them as ``1`` and
  ``0`` - by :user:`yuefdev`. (:issue:`4066`)
- Preserve an explicitly empty ``{factor:label:}`` fallback instead of using the declared factor group default.
  (:issue:`4072`)

.. _release-4-61-5-documentation:

Documentation
-------------

- ``Loader.build`` documented a ``future`` parameter it no longer takes and left ``factory`` undocumented, so the plugin
  API reference listed a parameter that does not exist - by :user:`hxperl`. (:issue:`4070`)

.. _release-4-61-4:

*********************
 4.61.4 (2026-09-09)
*********************

.. _release-4-61-4-fixed:

Fixed
-----

- Shebang parsing now uses ``shlex``, so a quoted interpreter path that contains spaces is kept as one argument when
  ``TOX_LIMITED_SHEBANG`` rewrites the invocation - by :user:`r3wretrhy`. (:issue:`4064`)

.. _release-4-61-3:

*********************
 4.61.3 (2026-09-08)
*********************

.. _release-4-61-3-fixed:

Fixed
-----

- A ``set_env`` environment file (``file|.env``) is now read as UTF-8 instead of the platform's locale encoding, so
  non-ASCII values no longer arrive mangled on Windows - by :user:`MohammedAlkindi`. (:issue:`4059`)
- Preserve UNC and extended-length paths in Windows commands, including quoted paths - by :user:`MohammedAlkindi`.
  (:issue:`4060`)
- Normalize project and extra names in dependency-group self-references - by :user:`MohammedAlkindi`. (:issue:`4061`)
- Register factor labels and defaults for bare labeled dicts in ``env_list`` - by :user:`dylanpulver`. (:issue:`4062`)

.. _release-4-61-2:

*********************
 4.61.2 (2026-08-31)
*********************

.. _release-4-61-2-fixed:

Fixed
-----

- tox now expands a generative digit range only where a factor starts, so an environment such as ``py313-django4-2``
  keeps its name rather than becoming ``py313-django4``, ``3`` and ``2`` - by :user:`MohammedAlkindi`. (:issue:`4053`)

.. _release-4-61-2-documentation:

Documentation
-------------

- Document how factors work in one place, covering what a factor is, the characters tox accepts in one, the platform and
  architecture factors that apply to conditions without appearing in a name, and how selecting by factor differs from
  selecting by name - by :user:`gaborbernat`. (:issue:`4055`)
- Give a reference entry to the configuration keys that had none. ``interrupt_post_commands`` runs ``commands_post``
  after an interrupt, and ``config_file_path``, ``host_python``, ``home`` and ``tox_root_name`` are constants a
  configuration can substitute - by :user:`gaborbernat`. (:issue:`4056`)

.. _release-4-61-1:

*********************
 4.61.1 (2026-08-28)
*********************

.. _release-4-61-1-fixed:

Fixed
-----

- Publish a JSON Schema that compiles under SchemaStore's validator again, so editors pick up the configuration keys
  added since 4.56 - by :user:`gaborbernat`. (:issue:`4051`)

.. _release-4-61-0:

*********************
 4.61.0 (2026-08-28)
*********************

.. _release-4-61-0-added:

Added
-----

- A labeled factor group can now declare a ``default`` for ``{factor:label}`` to fall back on when no factor of that
  group is active in the environment name. Setting ``TOX_FACTOR_<label>`` resolves that label to a given value for a
  single run - by :user:`gaborbernat`. (:issue:`4045`)
- A factor range now takes a label when you nest it under one, as in ``factors = [{ py_version = { prefix = "3.", start
  = 12, stop = 14 } }]``, which makes ``{factor:py_version}`` available for ranges - by :user:`gaborbernat`.
  (:issue:`4046`)

.. _release-4-61-0-fixed:

Fixed
-----

- Values passed via ``--override``/``-x`` or ``TOX_OVERRIDE`` now resolve substitutions such as ``{posargs}``,
  ``{env:VAR}`` and ``{env_name}``, instead of reaching the environment as literal text - by :user:`gaborbernat`.
  (:issue:`4047`)

.. _release-4-61-0-documentation:

Documentation
-------------

- Point the virtualenv discovery link in the explanation documentation at its current location. (:issue:`4042`)

.. _release-4-60-1:

*********************
 4.60.1 (2026-08-25)
*********************

.. _release-4-60-1-fixed:

Fixed
-----

- Report a malformed ``tox.ini`` or ``setup.cfg`` as a handled error during config discovery instead of raising an
  unhandled :class:`configparser.Error` traceback - by :user:`VXNCXNX` (:issue:`4027`)
- Report an invalid value in the ini ``[tox]`` core section (such as ``min_version``, ``requires`` or ``env_list``) as a
  handled error instead of an unhandled traceback, matching the existing TOML loader behavior - by :user:`VXNCXNX`
  (:issue:`4028`)
- Report an invalid ``--skip-env``/``TOX_SKIP_ENV`` regular expression as a handled error instead of raising an
  unhandled ``re.error`` traceback - by :user:`VXNCXNX` (:issue:`4029`)
- Keep ``;`` inside values read from a ``set_env`` environment file (``file|.env``). Environment file lines are plain
  ``KEY=VALUE`` pairs and were incorrectly parsed with the PEP-508 marker splitter, which truncated values such as
  ``DATABASE_URL=postgresql://host/db?opt=1;sslmode=require`` at the first semicolon - by :user:`VXNCXNX`
  (:issue:`4030`)
- Report a handled configuration error instead of leaking a traceback when the selected configuration file exists but
  cannot be read - by :user:`SirHegel`. (:issue:`4031`)
- Report an empty ``install_command`` or ``list_dependencies_command`` in a TOML configuration as a handled error
  instead of an unhandled traceback - by :user:`dylanpulver` (:issue:`4041`)

.. _release-4-60-0:

*********************
 4.60.0 (2026-08-13)
*********************

.. _release-4-60-0-added:

Added
-----

- Add ``{home}`` and ``{tox_root_name}`` substitutions; set :ref:`work_dir` to e.g.
  ``"{home}/.local/state/tox/{tox_root_name}"`` to keep environments outside of the project tree - by
  :user:`WhyNotHugo`. (:issue:`4020`)

.. _release-4-60-0-fixed:

Fixed
-----

- Provision the requested tox version before reading ``env_list``, allowing configuration syntax introduced by that
  version - by :user:`CAOShurong` (:issue:`4021`)

.. _release-4-60-0-documentation:

Documentation
-------------

- Fix nine source-code links in the onboarding guide that pointed at paths which no longer exist, and correct the class
  names of the TOML configuration sources and loaders they refer to - by :user:`Yusuf-Gadelrab`. (:issue:`4024`)

.. _release-4-59-0:

*********************
 4.59.0 (2026-08-10)
*********************

.. _release-4-59-0-added:

Added
-----

- The plugin and internal APIs now declare their types, and the code base passes ``mypy --strict`` and ``pyrefly`` next
  to ``ty`` - by :user:`gaborjbernat`.

  - :meth:`ConfigSet.get <tox.config.sets.ConfigSet.get>` returns a configuration value after checking it against its
    declared type, so plugins can drop ``cast`` around ``conf["key"]`` reads.
  - The :func:`tox_on_install <tox.plugin.spec.tox_on_install>` hook and :class:`Installer
    <tox.tox_env.installer.Installer>` type their ``arguments`` as :data:`InstallArguments
    <tox.tox_env.installer.InstallArguments>`; installer subclasses may narrow it through the new second type parameter.
  - :class:`Parsed <tox.config.cli.parser.Parsed>` declares the CLI option surface, so ``options.<name>`` reads
    type-check.
  - :meth:`ConfigSet.add_config <tox.config.sets.ConfigSet.add_config>` accepts ``default=None`` for optional values and
    infers the value type from callable defaults.
  - The journal, the environment cache, and execute metadata hold ``JsonValue`` content; structured ``set_env`` entries
    match the ``SetEnvEntry`` shape. (:issue:`4014`)

.. _release-4-59-0-documentation:

Documentation
-------------

- Mark the INI configuration format as deprecated throughout the documentation - by :user:`gaborbernat`.

  - The tutorial, the configuration reference, and the migration how-to state that INI keeps working for existing
    projects but is frozen and receives no new features.
  - Every INI example tab, the configuration discovery diagram, and the man page carry a deprecation marker.
  - The tutorial no longer suggests generating a ``tox.ini`` via ``tox quickstart``. (:issue:`4017`)

.. _release-4-58-0:

*********************
 4.58.0 (2026-07-21)
*********************

.. _release-4-58-0-added:

Added
-----

- Test against Python 3.15 (beta) in CI and declare its classifier - by :user:`gaborbernat`. (:issue:`4001`)

.. _release-4-57-2:

*********************
 4.57.2 (2026-07-21)
*********************

.. _release-4-57-2-fixed:

Fixed
-----

- Fix package environment creation failures being misreported:

  - discard the partially registered configuration on failure, so the real error surfaces instead of a spurious
    ``duplicate configuration definition``;
  - report the first creation failure in definition order, not a hash-random one;
  - build the PEP 517 frontend lazily, so ``tox c`` and ``tox l`` work when ``pyproject.toml`` cannot be read.
    (:issue:`3987`)

- Fix state corruption in the environment creation machinery:

  - a failed run environment build no longer removes shared package environments other run environments still use;
  - a run environment registers with its package environment once, not twice with triple-counted usage;
  - circular ``depends`` reports the cycle as an error instead of a raw traceback;
  - ``Skip`` raised by a plugin for a package environment marks the run environment package-skipped instead of crashing
    with ``UnboundLocalError``. (:issue:`3991`)

- Fix two packaging regressions:

  - ``package = editable`` on a build backend without PEP-660 support now falls back to ``editable-legacy`` with a
    warning instead of crashing, also when the project metadata is static;
  - editable and wheel environments running after an ``sdist-wheel`` environment build from the project sources again,
    instead of a stale temporary copy that made source edits invisible. (:issue:`3992`)

- An environment serving as both a run environment and a package environment now behaves predictably:

  - one defined through a ``[testenv:...]``-style section and referenced by ``package_env`` inherits from
    ``pkgenv``/``env_pkg_base`` as documented, instead of silently keeping run environment defaults;
  - one listed in ``env_list`` while referenced as a package environment is reported as a configuration conflict up
    front, instead of failing late with ``cannot run packaging environment`` or silently disappearing from ``tox l``.
    (:issue:`3993`)

- ``pylock.toml`` installs now match the lock file:

  - a package locked once per Python range installs only the version matching the environment's interpreter;
  - packages locked to a local directory, VCS repository, or archive install from that source instead of resolving the
    name against the package index;
  - locked hashes are verified when every entry carries one;
  - changing a pip environment variable such as ``PIP_INDEX_URL`` reinstalls, as it already did for ``deps``.
    (:issue:`3994`)

- Re-running tox no longer rebuilds an environment at random when ``deps`` uses ``--no-binary`` or ``--only-binary``
  with more than one package name. (:issue:`3995`)
- A corrupted environment status file (``.tox-info.json``) now always triggers an environment recreation instead of
  crashing tox with an internal error for some corruption shapes. (:issue:`3996`)
- PEP 723 scripts saved with a UTF-8 byte order mark now have their inline metadata honored (previously
  ``requires-python`` and ``dependencies`` were silently ignored), and a script with invalid metadata reports a clear
  configuration error instead of an internal one. (:issue:`3997`)
- Fix three command line defects:

  - ``tox c -o FILE`` writes the default (ini) format to the file like the json and toml formats, without color codes;
  - ``tox devenv -e ALL`` reports that exactly one environment is required instead of crashing;
  - ``--no-provision FILE`` records the pinned version for a ``tox==X`` requirement instead of an empty string.
    (:issue:`3998`)

- Restore the documented fail-fast contract and make cleanup resilient:

  - ``--fail-fast`` in parallel mode lets already running environments finish and report their real outcomes, instead of
    interrupting them after a second and mislabeling them as skipped;
  - environments canceled by fail fast before starting report as skipped;
  - the overall exit code under fail fast is the first failed environment's exit code, as documented;
  - one environment failing to clean up no longer prevents the remaining environments from cleaning up (which could
    leave tox hanging on exit). (:issue:`3999`)

- Polish four behaviors around the edges of a run:

  - an empty ``[tool.tox]`` stub in ``pyproject.toml`` no longer hides a ``tox.toml`` next to it;
  - setting ``CI=false`` (or empty) is respected as opting out of CI behavior;
  - spinner animation frames stay out of redirected output, which now holds plain text only;
  - the JSON report marks skipped environments with ``"skipped": true`` so they are distinguishable from passes.
    (:issue:`4000`)

.. _release-4-57-1:

*********************
 4.57.1 (2026-07-20)
*********************

.. _release-4-57-1-fixed:

Fixed
-----

- Stop a lone quote in a ``set_env`` value (e.g. an apostrophe in ``can't``) from swallowing the ``;`` platform marker,
  which silently set the variable unconditionally with the marker text left in the value - by :user:`chuenchen309`.
  (:issue:`3988`)
- Make ``tox run-parallel -p 0`` turn parallelism off and run sequentially, as the ``-p`` help ("zero is turn off") and
  the legacy command already promise, instead of running at the CPU count - by :user:`chuenchen309`. (:issue:`3989`)

.. _release-4-57-0:

*********************
 4.57.0 (2026-07-17)
*********************

.. _release-4-57-0-added:

Added
-----

- Support debug (``Py_DEBUG``) interpreters the way free-threaded builds are already handled. The ``py313d`` and
  ``py313td`` factors select a debug build, a ``base_python`` pointing at one matches those factors and conflicts with
  factors that lack the suffix, and a debug build gets its own ``d``-tagged wheel build environment - by
  :user:`chuenchen309`. (:issue:`3986`)

.. _release-4-57-0-fixed:

Fixed
-----

- Keep the free-threaded ``t`` suffix when deriving the base python spec from a path, so a ``base_python`` pointing at a
  free-threaded interpreter matches ``py313t`` factors and conflicts with factors that lack the suffix - by
  :user:`chuenchen309`. (:issue:`3986`)

.. _release-4-56-4:

*********************
 4.56.4 (2026-07-08)
*********************

.. _release-4-56-4-fixed:

Fixed
-----

- Discover debug (``Py_DEBUG``) interpreters set as ``base_python``, such as Debian's ``python3.13-dbg`` - the spec was
  misread as a machine named ``dbg`` and no interpreter matched. Requires ``python-discovery>=1.4.4`` - by
  :user:`gaborbernat`. (:issue:`3977`)

.. _release-4-56-3:

*********************
 4.56.3 (2026-07-08)
*********************

.. _release-4-56-3-fixed:

Fixed
-----

- Stop double-closing the child pty file descriptor when running under a tty, which could race a parallel run that had
  reused the freed descriptor number and cause intermittent ``Bad file descriptor``/``Input/output error`` failures - by
  :user:`apoorvdarshan`. (:issue:`3975`)

.. _release-4-56-2:

*********************
 4.56.2 (2026-07-07)
*********************

.. _release-4-56-2-fixed:

Fixed
-----

- Fix a batch of latent defects found in a codebase audit:

  - stop duplicating ``--extra-index-url`` when a merged requirements line repeats an already-seen index;
  - render ``--no-binary``/``--only-binary`` as comma-joined strings instead of leaking the internal ``set`` into the
    pip command line;
  - report a clear error instead of ``IndexError`` for a bare one-argument flag (``-c``, ``-r``, ``-f``, ``-e``) in
    ``deps`` or constraints;
  - canonicalize ``optional-dependencies`` keys and self-referential (recursive) extra names so non-canonical spellings
    no longer silently drop dependencies;
  - raise a clear error instead of ``KeyError`` when ``dependency_groups`` is requested without a
    ``[dependency-groups]`` table;
  - stop a native TOML ``{ replace = "env" }`` reference from leaking its resolution chain into sibling list entries and
    tripping a spurious ``circular chain`` error;
  - expand the range that actually matched in a factor expression rather than the first identical digit-range substring;
  - strip the backslash from an escaped ``\;`` in ``set_env`` values;
  - skip option values during command auto-detection so an environment named like a subcommand (e.g. ``tox -e list``) is
    no longer misread;
  - treat an empty list-typed environment variable (e.g. ``TOX_DISCOVER=``) as an empty list rather than ``[""]``;
  - report an environment whose name is an empty string as present in ``Config`` membership tests;
  - fail evaluation gracefully instead of crashing the driver thread when ``tox p -p all`` is run with an empty
    selection;
  - avoid rebuilding a throwaway PEP 517 frontend against the previous root when a package environment's ``root`` is
    reassigned before a frontend exists;
  - avoid crashing ``create_session_view`` when the package and its session copy share no common path (e.g. different
    Windows drives);
  - close the pseudo-terminal file descriptors that leaked on every command run under a tty and on the
    terminal-attribute inheritance error path;
  - honor the stop signal in the Windows overlapped-I/O reader while a read is still pending, so shutdown no longer
    risks hanging on a child that holds its pipe open without producing output. (:issue:`3974`)

.. _release-4-56-1:

*********************
 4.56.1 (2026-06-25)
*********************

.. _release-4-56-1-fixed:

Fixed
-----

- Fix ``{ replace = "if" ... extend = true }`` corrupting the resulting list when ``then`` or ``else`` is a scalar
  string (e.g. ``then = "-v"``): a non-empty scalar string is now appended as a single element instead of being iterated
  character-by-character, while a false ``if`` with no ``else`` (yielding ``""``) contributes nothing rather than an
  empty element, and list/set results are still spread into the parent. (:issue:`3969`)

.. _release-4-56-0:

*********************
 4.56.0 (2026-06-23)
*********************

.. _release-4-56-0-added:

Added
-----

- Derive :ref:`virtualenv_spec` automatically: when an environment targets a Python version the installed
  :pypi:`virtualenv` can no longer create (e.g. ``py38`` with virtualenv ``21.5+``), tox now pins the newest virtualenv
  that still supports it and bootstraps it for that environment only. The downgrade happens only when every
  ``base_python`` candidate is unsupported, so environments targeting current interpreters are unaffected. This fixes
  ``py38`` (and other end-of-life interpreters) being silently skipped after a virtualenv upgrade - by
  :user:`gaborbernat`. (:issue:`3965`) (:issue:`3965`)

.. _release-4-56-0-fixed:

Fixed
-----

- The default value of ``skip_missing_interpreters`` changed from ``True`` to ``False`` — missing interpreters now fail
  the run by default, matching tox 3 behavior. The tox 4 rewrite unintentionally changed this default. To restore the
  previous (incorrect) behavior, set ``skip_missing_interpreters = true`` in your tox configuration or pass
  ``--skip-missing-interpreters`` on the command line. (:issue:`3965`)

.. _release-4-56-0-documentation:

Documentation
-------------

- Fix nested list items being rendered with continued numbering instead of as sub-items in ``development.rst``,
  ``onboarding.rst`` and ``explanation.rst``. (:issue:`3960`)
- Replace stale ``http://tox.readthedocs.org`` URL with ``https://tox.wiki`` in ``pyproject.toml`` (``Homepage``),
  ``.github/CONTRIBUTING.md``, and ``.github/PULL_REQUEST_TEMPLATE.md``. (:issue:`3963`)

.. _release-4-55-1:

*********************
 4.55.1 (2026-06-03)
*********************

.. _release-4-55-1-fixed:

Fixed
-----

- ``TOX_OVERRIDE`` (and ``-x``/``--override``) now propagates through configuration references. Previously, overriding a
  base value that was later referenced via ``{[section]key}`` (ini) or ``{replace = "ref", of = [...]}`` (toml) was
  ignored because reference resolution read the raw file value, bypassing the override system - by
  :user:`tales-aparecida`. (:issue:`3950`) (:issue:`3950`)

.. _release-4-55-0:

*********************
 4.55.0 (2026-05-28)
*********************

.. _release-4-55-0-added:

Added
-----

- Automatically pass the TERMINFO environment variable to tox subprocesses if the output is a TTY. This variable is used
  by Ghostty to communicate terminal capabilities to programs. (:issue:`3946`)

.. _release-4-55-0-fixed:

Fixed
-----

- When the ``constraints`` configuration option is set, ``constrain_package_deps`` and ``use_frozen_constraints`` are
  now ignored. Previously, both the user-provided constraints file and the auto-generated constraints file were passed
  to pip during ``install_package_deps``, which could cause resolver conflicts when the same package appeared in both
  files - by :user:`gaborbernat`. (:issue:`3945`) (:issue:`3945`)

.. _release-4-54-0:

*********************
 4.54.0 (2026-05-12)
*********************

.. _release-4-54-0-added:

Added
-----

- Declare the runtime dependencies of the ``tox.pytest`` plugin (``pytest``, ``devpi-process`` and ``pytest-mock``)
  under a new ``testing`` extra, so plugin authors can pull them in via ``tox[testing]`` - by :user:`gaborbernat`.
  (:issue:`3938`, :issue:`3940`)

.. _release-4-54-0-fixed:

Fixed
-----

- Extend the generated TOML schema to cover every ``replace`` table form (``env``, ``ref``, ``posargs``, ``glob``,
  ``if``), including conditional replacements used inside ``commands``. A guard test asserts the schema stays in sync
  with the loader implementation so future replace types cannot be added without a corresponding schema entry.
  (:issue:`3939`)

.. _release-4-53-1:

*********************
 4.53.1 (2026-05-02)
*********************

.. _release-4-53-1-fixed:

Fixed
-----

- Hardening pass on user-facing logging and config parsing:

  - Mask secret-looking ``--key=value`` flag values in command logs (terminal warnings, ``.tox/<env>/log/*.log``, and
    ``Outcome`` ``__repr__``) using the same keyword regex previously applied to environment variable values.
  - Resolve PEP 723 ``script`` paths and reject any that escape ``tox_root``; cap the script read at 5 MiB so a symlink
    to ``/dev/zero`` cannot exhaust memory.
  - Replace ``eval()`` of a constructed ``Literal[...]`` string in the CLI parser with a direct
    ``Literal[tuple(action.choices)]`` subscript.
  - Pass ``timeout=30`` to ``urlopen`` when fetching a remote requirements file so a slow or unresponsive mirror cannot
    hang ``tox`` indefinitely. (:issue:`3924`)

- Allow the generated TOML schema to validate array values for ``deps``. (:issue:`3929`)
- Correct type annotations for ``ArgumentParser.parse_args`` and ``parse_known_args`` overrides following `typeshed PR
  #15613 <https://github.com/python/typeshed/pull/15613>`_, which widened the ``args`` parameter from ``Sequence[str]``
  to ``Iterable[str]``. The narrower type in tox's overrides violated the Liskov substitution principle and caused
  ``invalid-method-override`` errors with ``ty`` 0.0.33. Also correct the ``option_spec`` annotation in
  ``docs/tox_conf.py`` to ``ClassVar[dict[str, Callable[[str], Any]]]`` matching the docutils stubs type.
  (:issue:`3932`)

.. _release-4-53-0:

*********************
 4.53.0 (2026-04-14)
*********************

.. _release-4-53-0-added:

Added
-----

- TOML ``env_list`` now accepts bare range dicts (``{ prefix = "3.", start = 12, stop = 14 }``) and bare labeled dicts
  (``{ ecosystem = ["oci", "python"] }``) as top-level items, removing the ``{ product = [...] }`` wrapper when there is
  only a single factor group - by :user:`gaborbernat`. (:issue:`3923`)

.. _release-4-53-0-fixed:

Fixed
-----

- Nesting a range or labeled dict inside a ``product`` factor-group list now raises a clear error pointing at the
  un-nesting fix, instead of silently producing a malformed environment name - by :user:`gaborbernat`. (:issue:`3923`)

.. _release-4-52-1:

*********************
 4.52.1 (2026-04-09)
*********************

.. _release-4-52-1-fixed:

Fixed
-----

- Changing a resolution-affecting environment variable via ``set_env`` (e.g. ``PIP_INDEX_URL``) now invalidates the
  install cache and triggers a reinstall, rather than incorrectly reusing the cached environment - by
  :user:`gaborbernat`. (:issue:`3917`)
- Use ``normalize_isa`` from ``python-discovery`` for architecture factor matching, supporting aliases like ``i686`` →
  ``x86`` and ``aarch64`` → ``arm64`` - by :user:`rahuldevikar`. (:issue:`3919`)

.. _release-4-52-0:

*********************
 4.52.0 (2026-03-30)
*********************

.. _release-4-52-0-added:

Added
-----

- Add ``virtualenv-pep-723`` runner that reads dependencies and Python version from :PEP:`723` inline script metadata —
  no need to duplicate them in tox config - by :user:`gaborbernat`. (:issue:`3897`)
- Support escaped dots (``\.``) in ``-x``/``--override`` keys, allowing overrides to target environments with dots in
  their names such as ``py3.14`` - by :user:`gaborbernat`. (:issue:`3910`)

.. _release-4-52-0-fixed:

Fixed
-----

- Auto-generate the manpage from the CLI argparse parser at wheel build time, fixing broken section headers and
  documenting all commands and options - by :user:`gaborbernat`. (:issue:`3878`)

.. _release-4-51-0:

*********************
 4.51.0 (2026-03-27)
*********************

.. _release-4-51-0-added:

Added
-----

- Add ``base_python_file`` configuration option to read the base Python version from a file (e.g. ``.python-version``),
  similar to GitHub Actions' ``python-version-file`` - by :user:`rahuldevikar` (:issue:`3894`)

.. _release-4-51-0-fixed:

Fixed
-----

- Prevent implicit machine ISA (e.g. ``arm64``, ``x86_64``) from overriding explicit architecture factors in environment
  names, fixing cross-architecture conflicts in multiline factor conditionals - by :user:`rahuldevikar`. (:issue:`3903`)
- Nested environment list configuration values are now properly parsed, validated and expanded by the TOML parser. This
  allows you to use generative environment lists in ``tox-gh`` via the TOML format. Previously this was only possible
  with the INI format. - by :user:`Daverball` (:issue:`3905`)

.. _release-4-50-3:

*********************
 4.50.3 (2026-03-20)
*********************

.. _release-4-50-3-fixed:

Fixed
-----

- Use separate ``.pkg`` environments for free-threaded Python targets by including the ``t`` suffix in the wheel build
  environment name (e.g., ``.pkg-cpython314t``), preventing wheel tag mismatches when building for ``py314t`` - by
  :user:`gaborbernat`. (:issue:`3314`)

.. _release-4-50-2:

*********************
 4.50.2 (2026-03-19)
*********************

.. _release-4-50-2-fixed:

Fixed
-----

- Fix the sdist to include the missing ``docs/man/tox.1.rst`` file for building the manpage (:issue:`3889`)

.. _release-4-50-1:

*********************
 4.50.1 (2026-03-19)
*********************

.. _release-4-50-1-fixed:

Fixed
-----

- Detect and suggest normalized environment names when users specify dotted Python versions (e.g., ``py3.10-lint``) that
  match existing environments with compact notation (e.g., ``py310-lint``), preventing silent fallback to base
  ``[testenv]`` configuration - by :user:`gaborbernat`. (:issue:`3877`)

.. _release-4-50-0:

*********************
 4.50.0 (2026-03-17)
*********************

.. _release-4-50-0-added:

Added
-----

- Add ``interrupt_post_commands`` option to run cleanup commands even after SIGINT - by :user:`gaborbernat`.
  (:issue:`3858`)
- Add ``factor['NAME']`` and ``env['VAR']`` subscript syntax for conditional expressions, enabling checks of factors
  with non-identifier names like ``factor['3.14']``. Add ``env_name`` variable to check the full environment name in
  conditions. (:issue:`3880`)

.. _release-4-50-0-fixed:

Fixed
-----

- Fix multiple manpage issues: remove duplicate header/author/copyright sections, set ``project`` in Sphinx config, and
  compile the manpage to troff format at wheel-build time instead of shipping raw RST source - by :user:`gaborbernat`.
  (:issue:`3878`)

.. _release-4-50-0-documentation:

Documentation
-------------

- Document how to reference the built package path in commands via ``TOX_PACKAGE`` - by :user:`rahuldevikar`
  (:issue:`3862`)
- Fix broken TOML examples missing ``extend = true`` on conditional replacements inside lists, fix incorrect ``ref of``
  path in raw reference docs, and add a test that validates all doc config examples - by :user:`gaborbernat`
  (:issue:`3875`)

.. _release-4-49-1:

*********************
 4.49.1 (2026-03-09)
*********************

.. _release-4-49-1-fixed:

Fixed
-----

- Break deadlock in execution interrupt chain that caused ~18 flaky timeout failures across 9 tests on Windows/macOS CI
  by :user:`gaborbernat`. (:issue:`3869`)

.. _release-4-49-0:

*********************
 4.49.0 (2026-03-06)
*********************

.. _release-4-49-0-added:

Added
-----

- Add ``{factor:label}`` substitution for TOML configs -- factor groups in ``product`` matrices and ``env_base`` factors
  can now be labeled with single-key dicts (e.g., ``{ecosystem = ["oci", "python"]}``), enabling ``{factor:ecosystem}``
  in any string value (descriptions, commands, etc.) to resolve to the active factor. Plain lists automatically get
  positional labels (``{factor:0}``, ``{factor:1}``, ...) - by :user:`gaborbernat`. (:issue:`3860`) (:issue:`3860`)

.. _release-4-49-0-fixed:

Fixed
-----

- Fix ``--showconfig`` and ``--help-ini`` legacy flags raising ``AttributeError`` after config format options were added
  by :user:`rares985` (:issue:`3866`)

.. _release-4-48-1:

*********************
 4.48.1 (2026-03-06)
*********************

.. _release-4-48-1-fixed:

Fixed
-----

- Command-type configuration values like ``list_dependencies_command`` can now be referenced in TOML using the
  structured ``{replace = "ref"}`` syntax. The reference automatically extracts the command's argument list for
  compatibility with TOML's ``list[list[str]]`` structure - by :user:`gaborbernat`. (:issue:`3830`)

.. _release-4-48-1-documentation:

Documentation
-------------

- Replace archived ``31z4/tox`` Docker image recommendation with instructions for building your own image using the
  official Python base image and ``uv`` - by :user:`rahuldevikar`. (:issue:`3855`)

.. _release-4-48-0:

*********************
 4.48.0 (2026-03-05)
*********************

.. _release-4-48-0-added:

Added
-----

- Add ``--format`` flag (``ini``, ``json``, ``toml``) and ``-o``/``--output-file`` to the ``config`` command for
  machine-readable output with native types. JSON and TOML use the same key structure as ``tox.toml`` (``env.<name>``
  for environments, ``tox`` for core) and get syntax-highlighted on stdout - by :user:`gaborbernat`. (:issue:`3854`)

.. _release-4-48-0-documentation:

Documentation
-------------

- Add ``fail_fast`` to the configuration reference documentation - by :user:`rahuldevikar`. (:issue:`578`)

.. _release-4-47-3:

*********************
 4.47.3 (2026-03-04)
*********************

.. _release-4-47-3-fixed:

Fixed
-----

- ``ignore_base_python_conflict`` now also suppresses errors when an environment name contains multiple conflicting
  version-like factors (e.g., ``unit-py3.10-2.16`` where both ``py3.10`` and ``2.16`` are detected as Python versions).
  Previously this flag only handled conflicts between explicit ``base_python`` settings and the environment name - by
  :user:`gaborbernat`. (:issue:`3850`)

.. _release-4-47-2:

*********************
 4.47.2 (2026-03-03)
*********************

.. _release-4-47-2-fixed:

Fixed
-----

- Handle ``OSError`` when checking if positional arguments are existing paths in ``pos_args()`` — long arguments (e.g.,
  pytest ``-k`` expressions exceeding the 255-character filesystem name limit) no longer crash with ``OSError: [Errno
  36] File name too long`` - by :user:`yarikoptic`. (:issue:`3847`)

.. _release-4-47-1:

*********************
 4.47.1 (2026-03-03)
*********************

.. _release-4-47-1-fixed:

Fixed
-----

- New-style version factors (e.g., ``3.10-tests``) now correctly set ``base_python`` - by :user:`gaborbernat`.
  (:issue:`3845`)

.. _release-4-47-0:

*********************
 4.47.0 (2026-03-01)
*********************

.. _release-4-47-0-added:

Added
-----

- Show clean error messages instead of stack traces when TOML configuration contains type mismatches (e.g., ``deps =
  [1]``), wrapping failures in ``HandledError`` with environment and key context - by :user:`gaborbernat`.
  (:issue:`3831`)
- Add comprehensive tests asserting full error messages for every configurable field type when TOML config contains type
  mismatches - by :user:`gaborbernat`. (:issue:`3840`)

.. _release-4-47-0-fixed:

Fixed
-----

- Fix type errors flagged by ``ty`` for ``virtualenv`` API changes (``system_executable`` nullability and
  ``cached_py_info.PythonInfo`` removal), and correct the CI workflow matrix exclude for ``windows-2025`` - by
  :user:`gaborbernat`. (:issue:`3837`)
- ``base_python`` and ``default_base_python`` now accept a string value in TOML configuration (e.g., ``base_python =
  "python"`` is coerced to ``["python"]``) instead of raising ``TypeError`` - by :user:`gaborbernat`. (:issue:`3839`)
- Pass stdin through to commands executed via ``tox exec`` so that piped input (e.g., ``echo "foo" | tox exec -- python
  -c 'import sys; print(sys.stdin.read())'``) reaches the subprocess instead of being discarded - by
  :user:`gaborbernat`. (:issue:`3841`)

.. _release-4-46-3:

*********************
 4.46.3 (2026-02-25)
*********************

.. _release-4-46-3-fixed:

Fixed
-----

- Fix SchemaStore update workflow creating PRs with merge conflicts by branching from upstream master - by
  :user:`gaborbernat`. (:issue:`3828`)
- Fixed the minimum version of virtualenv, to avoid incompatibility. (:issue:`3829`)

.. _release-4-46-2:

*********************
 4.46.2 (2026-02-25)
*********************

.. _release-4-46-2-fixed:

Fixed
-----

- Fix SchemaStore update workflow authentication and PR creation for fork repositories - by :user:`gaborbernat`.
  (:issue:`3826`)

.. _release-4-46-1:

*********************
 4.46.1 (2026-02-25)
*********************

.. _release-4-46-1-fixed:

Fixed
-----

- Allow glob patterns (``*``, ``?``) in ``depends`` configuration for ini files - by :user:`gaborbernat`.
  (:issue:`3822`)
- Fix false positive schema validation errors with tombi by adding ``additionalProperties: true`` to
  ``partial-tox.json`` on SchemaStore - by :user:`gaborbernat`. (:issue:`3823`)

.. _release-4-46-0:

*********************
 4.46.0 (2026-02-24)
*********************

.. _release-4-46-0-added:

Added
-----

- Add architecture (ISA) awareness to Python discovery. tox now propagates the ``machine`` field (e.g. ``arm64``,
  ``x86_64``) from :pypi:`virtualenv`'s interpreter info — derived from :func:`python:sysconfig.get_platform` — through
  the Python specification, validation, and journal. This allows selecting a Python interpreter by CPU architecture via
  :ref:`base_python` (e.g. ``cpython3.12-64-arm64``) and ensures tox validates the running interpreter's architecture
  matches the requested one. Requires ``virtualenv >= 20.39`` - by :user:`rahuldevikar`. (:issue:`3069`)
- Add ``env_base`` TOML sections for named environment templates that generate multiple environments from factor
  combinations via Cartesian product -- by :user:`gaborbernat`. (:issue:`3817`)

.. _release-4-46-0-fixed:

Fixed
-----

- Drop ``chardet`` dependency and use BOM detection with locale fallback for requirements file decoding, matching pip's
  own approach - by :user:`gaborbernat`. (:issue:`3818`)
- Allow ``--help`` to render even when the configuration file is malformed or missing - by :user:`gaborbernat`.
  (:issue:`3819`)

.. _release-4-45-0:

*********************
 4.45.0 (2026-02-23)
*********************

.. _release-4-45-0-added:

Added
-----

- Enhance ``tox schema`` command: add ``x-taplo`` metadata for IDE integration, product dict support for ``env_list``,
  handle ``int`` and ``PythonConstraints`` types, fix ``$schema`` draft-07 URI, and add schema freshness test. Add
  ``tox.toml`` to SchemaStore catalog for automatic IDE validation - by :user:`gaborbernat`. (:issue:`1388`)

.. _release-4-45-0-fixed:

Fixed
-----

- Add redirects for old documentation URLs that broke after the Diataxis restructure (e.g. ``/config.html`` ->
  ``/reference/config.html``, ``/example/general.html`` -> ``/index.html``) using ``sphinx-reredirects`` - by
  :user:`gaborbernat`. (:issue:`3806`)
- Fix cross-section substitution ``{[section]key}`` resolving to a literal unresolved reference instead of empty string
  when the referenced value contains only factor-conditional lines and no factors match the requesting environment - by
  :user:`Fridayai700`. (:issue:`3809`)
- Fix circular dependency in ``environment_variables`` when ``set_env`` references ``{env_site_packages_dir}`` or
  similar lazy constants, causing ``RecursionError`` silently caught as "could not find python interpreter" - by
  :user:`gaborbernat`. (:issue:`3816`)

.. _release-4-44-0:

*********************
 4.44.0 (2026-02-20)
*********************

.. _release-4-44-0-added:

Added
-----

- Support PEP 751 ``pylock.toml`` lock files as dependency input via the ``pylock`` configuration option (mutually
  exclusive with ``deps``). Packages are filtered by extras, dependency groups, and platform markers evaluated against
  the target Python interpreter, then installed via pip with ``--no-deps`` - by :user:`gaborbernat`. (:issue:`3665`)

.. _release-4-44-0-fixed:

Fixed
-----

- Fix unfactored continuation lines (e.g. ``pytest \``, ``--remote-data \``) being incorrectly skipped when they follow
  a filtered factor-conditional line ending with ``\`` -- the ``pending_skip`` flag now only drops terminal continuation
  pieces, preserving shared arguments that are themselves continuations - by :user:`gaborbernat`. (:issue:`3802`)

.. _release-4-43-0:

*********************
 4.43.0 (2026-02-20)
*********************

.. _release-4-43-0-added:

Added
-----

- Add TOML-native generative ``env_list`` via ``product`` dict syntax -- Cartesian product of factor groups with
  optional range dicts and exclusions - by :user:`gaborbernat`. (:issue:`3797`)

.. _release-4-43-0-fixed:

Fixed
-----

- Pass ``config_settings_build_wheel`` to pip as ``--config-settings`` when installing sdist packages, ensuring the
  build backend receives config settings during pip's internal wheel build - by :user:`gaborbernat`. (:issue:`3125`)
- Fix factor-conditional continuation lines (e.g. ``cov: coverage run \`` / ``!cov: python \`` / ``somefile.py``) where
  different factor prefixes on consecutive continuation lines caused prefixes to be passed as literal command arguments
  instead of being filtered - by :user:`gaborbernat`. (:issue:`3796`)

.. _release-4-43-0-documentation:

Documentation
-------------

- Integrate ``sphinxcontrib-towncrier`` to render draft changelog entries directly in Sphinx, replacing the manual
  towncrier draft script - by :user:`gaborbernat`. (:issue:`3201`)

.. _release-4-42-0:

*********************
 4.42.0 (2026-02-20)
*********************

.. _release-4-42-0-added:

Added
-----

- Platform-dependent commands can now be specified using factor syntax without requiring the platform name in the
  environment name. The current platform (``sys.platform`` value like ``linux``, ``darwin``, ``win32``) is automatically
  available as an implicit factor, allowing configurations like ``linux: pytest`` in INI or ``factor.linux`` in TOML
  conditional expressions to work in any environment. Additionally, TOML configurations can now use ``factor.NAME`` in
  conditional expressions to filter settings based on environment name factors, achieving feature parity with INI's
  factor system - by :user:`gaborbernat`. (:issue:`2092`)
- Add ``{env_site_packages_dir_plat}`` / ``{envsitepackagesdir_plat}`` substitution that returns the platform-specific
  (platlib) site-packages directory. On some Linux distributions (Fedora, RHEL) this resolves to ``lib64`` instead of
  ``lib``, which is no longer symlinked since virtualenv 20.x - by :user:`gaborbernat`. (:issue:`2302`)
- External packaging environments (``package = external``) now only run their build commands once per session, reusing
  the built package for all test environments that depend on them - by :user:`gaborbernat`. (:issue:`2729`)
- Add ``default_base_python`` configuration key to specify a fallback Python interpreter when no Python factor or
  explicit ``base_python`` is defined. This allows projects to pin a default Python version for reproducibility across
  different machines without conflicting with ``pyXY`` factor-named environments - by :user:`gaborbernat`.
  (:issue:`2846`)
- CLI options added by plugins listed in ``requires`` are now accepted during provisioning instead of failing with
  "unrecognized arguments" - by :user:`gaborbernat`. (:issue:`2935`)
- Warn about unused configuration keys during ``tox run -v`` - by :user:`gaborbernat`. (:issue:`3188`)
- Improve towncrier changelog structure with more granular categories: ``breaking``, ``deprecation``, ``feature``,
  ``bugfix``, ``doc``, ``packaging``, ``contrib``, and ``misc`` - by :user:`gaborbernat`. (:issue:`3200`)
- Add ``--skip-env-install`` CLI flag to skip dependency and package installation, allowing reuse of existing
  environments when offline or when installation is unnecessary - by :user:`gaborbernat`. (:issue:`3310`)
- Add ``recreate_commands`` configuration option to run cleanup commands (e.g. clearing external caches like pre-commit)
  before the environment directory is removed during recreation (``-r``) - by :user:`gaborbernat`. (:issue:`3423`)
- Environments with unavailable runners (missing plugins) are now gracefully skipped instead of causing a fatal error,
  shown with status "NOT AVAILABLE". If such an environment is explicitly requested with ``-e``, a clear error message
  is shown indicating which runner is missing and that the plugin may not be installed. Unavailable environments in the
  configuration don't cause the overall run to fail - by :user:`gaborbernat`. (:issue:`3504`)
- Add open-ended range expansion in generative env lists — ``py3{9-}`` expands up to the latest supported CPython minor
  version and ``py3{-13}`` expands down to the oldest supported one, both hardcoded at release time per the `Python
  release cycle <https://devguide.python.org/versions/>`_ - by :user:`gaborbernat`. (:issue:`3583`)
- Add ``--no-capture`` (``-i``) CLI flag to disable output capture, allowing interactive programs like Python REPL to
  access the terminal directly. When enabled, subprocess inherits parent console handles instead of pipes, fixing issues
  where terminal APIs (e.g., querying console dimensions) fail on pipe handles. Mutually exclusive with
  ``--result-json`` and parallel mode - by :user:`gaborjbernat`. Fixes :issue:`3635`. (:issue:`3635`)
- Add ``virtualenv_spec`` configuration key that allows pinning a specific virtualenv version per environment (e.g.
  ``virtualenv_spec = "virtualenv<20.22.0"``). When set, tox bootstraps the specified version in an isolated environment
  and drives it via subprocess, enabling environments targeting Python versions incompatible with the installed
  virtualenv - by :user:`gaborbernat`. (:issue:`3656`)

.. _release-4-42-0-fixed:

Fixed
-----

- Suppress ``BrokenPipeError`` during backend teardown when interrupted, preventing traceback spam during
  KeyboardInterrupt - by :user:`gaborjbernat`. Fixes :issue:`2660`. (:issue:`2660`)
- Factor-specific multiline commands using backslash continuation (``\``) no longer leak continuation lines into
  environments that don't match the factor - by :user:`gaborbernat`. (:issue:`2912`)
- ``--list-dependencies`` output is now printed to stdout during parallel runs. Previously, the dependency list was
  captured in suspended output buffers and only shown on failure - by :user:`gaborbernat`. (:issue:`3322`)
- Compound factor conditionals (e.g., ``np-cov: coverage``) now correctly allow their individual factors to be used when
  specifying environments with ``-e``. Previously, running ``tox -e py310-np-cov`` with a factor conditional ``np-cov:
  coverage`` in the config would fail with "provided environments not found" because the individual factor ``cov`` was
  not recognized as combinable - by :user:`gaborbernat`. (:issue:`3780`)

.. _release-4-42-0-documentation:

Documentation
-------------

- Document Debian/Ubuntu ``python3-venv`` limitation in known limitations - by :user:`gaborbernat`. (:issue:`3195`)

.. _release-4-41-0:

*********************
 4.41.0 (2026-02-19)
*********************

.. _release-4-41-0-added:

Added
-----

- Add ``package = "deps-only"`` mode that installs the package's dependencies (including extras) without building or
  installing the package itself. For projects with static :PEP:`621` metadata, dependencies are read directly from
  ``pyproject.toml`` without creating a packaging environment - by :user:`gaborbernat`. (:issue:`2301`)
- Prefer TOML-native configuration (``[tool.tox]``) over ``legacy_tox_ini`` when both are present in ``pyproject.toml``,
  allowing users to include a ``legacy_tox_ini`` section with ``min_version`` for older tox versions while using native
  TOML config for newer ones - by :user:`rahuldevikar`. (:issue:`3402`)

.. _release-4-41-0-fixed:

Fixed
-----

- Fix PEP 517 backend crash detection to handle both ``ENOENT`` (missing interpreter) and runtime crashes without
  hanging, and fix flaky ``test_provision_install_pkg_pep517`` integration test by using a pre-built wheel instead of an
  sdist to avoid devpi mirror dependency on setuptools - by :user:`gaborjbernat`. (:issue:`3774`)

.. _release-4-40-0:

*********************
 4.40.0 (2026-02-19)
*********************

.. _release-4-40-0-added:

Added
-----

- Add ``{glob:PATTERN}`` substitution to expand file system glob/wildcard patterns in configuration values. Supports
  default values, recursive ``**`` matching, and both INI string syntax and TOML dict syntax (``{ replace = "glob",
  pattern = "..." }``) - by :user:`gaborbernat`. (:issue:`1571`)
- Add ``commands_retry`` configuration option to automatically retry failed commands - by :user:`gaborbernat`.
  (:issue:`1578`)
- Automatically create a ``.gitignore`` file containing ``*`` in the tox work directory (typically ``.tox/``) and in
  environment info directories, so that tox-managed files are not tracked by git - by :user:`rahuldevikar`.
  (:issue:`2530`)
- Add conditional value selection via ``replace = "if"`` in TOML configuration. Supports a ``condition`` expression with
  ``env.VAR`` lookups, ``==``/``!=`` comparisons, and ``and``/``or``/``not`` boolean logic to select between ``then``
  and ``else`` values - by :user:`gaborbernat`. (:issue:`3650`)
- Add ``sdist-wheel`` package type that builds a wheel from a source distribution, ensuring the sdist is complete and
  the package can be correctly built from it — by :user:`rahuldevikar`. (:issue:`3687`)

.. _release-4-40-0-fixed:

Fixed
-----

- Use positive exit code (``1``) instead of ``-1`` when reporting failures across multiple environments. On Windows,
  ``cmd.exe``'s ``IF ERRORLEVEL 1`` only matches exit codes ``>= 1``, so the previous negative exit code was silently
  treated as success - by :user:`radevika`. Fixes :issue:`2945`. (:issue:`2945`)
- When ``set_env`` both inherits via cross-section substitution (e.g., ``{[testenv]set_env}``) and explicitly overrides
  the same variable, the explicit value was incorrectly replaced by the inherited one because ``load()`` moved the key
  from the raw dict to the materialized dict before the deferred substitution ran, making the protection check
  ineffective - by :user:`gaborjbernat`. Fixes :issue:`3773`. (:issue:`3773`)

.. _release-4-39-0:

*********************
 4.39.0 (2026-02-18)
*********************

.. _release-4-39-0-added:

Added
-----

- Create a ``CACHEDIR.TAG`` file in the tox work directory (``.tox``) so that backup and archiving tools (e.g., ``tar
  --exclude-caches``, Borg, restic) can automatically skip it - by :user:`radevika`. (:issue:`3334`)

.. _release-4-39-0-fixed:

Fixed
-----

- On Windows, ANSI color codes from child processes (like pytest, mypy) are now rendered correctly in terminals by
  enabling VT100 processing mode for subprocess output streams - by :user:`gaborbernat`. (:issue:`2337`)
- Concurrent tox processes no longer corrupt the provision environment (``.tox``) -- a file lock now serializes
  provisioning across processes - by :user:`gaborbernat`. (:issue:`2515`)
- Config files (``tox.ini``, ``setup.cfg``) with unicode characters are now read correctly on Windows when running tox
  with ``python -m -I`` (isolation mode) - by :user:`gaborbernat`. (:issue:`2692`)
- ``set_env`` values explicitly defined in a section now take precedence over values inherited via cross-section
  substitution (e.g., ``{[testenv]set_env}``) - by :user:`gaborbernat`. (:issue:`2831`)
- The ``-e`` flag now supports brace expansion (e.g. ``tox -e 'py{38,39}-pytest{6.x,7.x}'``) instead of incorrectly
  splitting on commas inside braces - by :user:`gaborbernat`. (:issue:`2850`)
- Posargs containing colons no longer crash tox when an inactive environment uses ``{posargs}`` in path-like
  configuration values such as ``env_dir`` - by :user:`gaborbernat`. (:issue:`2860`)
- ``set_env`` values from cross-section substitution (e.g., ``{[testenv]set_env}``) now correctly override default
  environment variables like ``PYTHONHASHSEED`` - by :user:`gaborbernat`. (:issue:`2872`)
- ``--force-dep`` now applies to package dependencies from project metadata (e.g. ``setup.cfg`` ``install_requires``,
  ``pyproject.toml`` ``dependencies``), not just tox config ``deps`` - by :user:`gaborbernat`. (:issue:`2943`)
- Using ``{posargs}`` in ``change_dir`` no longer causes a ``RecursionError`` - by :user:`gaborbernat`. (:issue:`3062`)
- Cross-section substitution (e.g. ``{[testenv:a]commands}``) now resolves environment-specific variables like
  ``{envpython}``, ``{envbindir}``, ``{envtmpdir}``, and ``{envsitepackagesdir}`` in the calling environment's context
  rather than the referenced environment's context - by :user:`gaborbernat`. (:issue:`3075`)
- Fix ``ValueError`` crash when using posargs on Windows with ``subst`` drive mappings -- ``os.path.relpath`` fails
  across drive letters, so fall back to absolute paths when the relative path cannot be computed - by
  :user:`gaborbernat`. (:issue:`3086`)
- ``TOX_OVERRIDE`` with ``+=`` (append) now works correctly when the override key name differs from the config file key
  name (e.g., overriding ``pass_env`` when config uses ``passenv``, or vice versa) - by :user:`gaborbernat`.
  (:issue:`3127`)
- Fix spurious environment discovery from non-tox sections in ``setup.cfg`` -- ``packages = find:`` in ``[options]`` was
  incorrectly interpreted as a tox factor marker, creating a phantom ``find`` environment - by :user:`gaborbernat`.
  (:issue:`3134`)
- Requirements in ``requires`` with environment markers that evaluate to false (e.g. ``virtualenv<20.22.0;
  python_version < "3.8"``) are now correctly skipped during provisioning instead of causing an infinite provisioning
  loop - by :user:`gaborbernat`. (:issue:`3136`)
- Running environments with ``recreate = true`` no longer destroys shared package environments (e.g. ``.pkg``), which
  previously caused ``FileNotFoundError`` when a subsequent environment tried to use the already-built wheel - by
  :user:`gaborbernat`. (:issue:`3146`)
- Factor-conditional config values (e.g. ``base_python = py312: python3.12``) now correctly fall back to the default
  when no factors match the current environment, instead of producing an empty value - by :user:`gaborbernat`.
  (:issue:`3189`)
- ``TOX_PARALLEL_NO_SPINNER`` / ``--parallel-no-spinner`` no longer forces parallel mode in the legacy command, fixing
  output suppression for sequential runs in CI - by :user:`gaborbernat`. (:issue:`3193`)
- Multiple ``-e`` flags are now additive (``tox r -e a -e b`` runs both ``a`` and ``b``), matching tox 3 behavior - by
  :user:`gaborbernat`. (:issue:`3199`)
- Environments like ``functional-py312`` no longer incorrectly match when only ``functional{-py310}`` is defined as a
  testenv section -- factors from section headers are no longer treated as freely combinable with CLI ``-e`` selections
  by :user:`gaborbernat`. (:issue:`3219`)
- On Windows, a trailing path separator (e.g. from ``{/}``) no longer causes the next command argument to be merged into
  the path - backslash before whitespace is now treated as a literal path separator rather than a space escape - by
  :user:`gaborbernat`. (:issue:`3222`)
- Fix ``{envtmpdir}`` and other env variable substitutions not expanding in external package environment commands - by
  :user:`gaborbernat`. (:issue:`3238`) (:issue:`3238`)
- On Windows, colored output is now preserved when running provisioned tox by explicitly passing the ``--colored yes``
  flag to the provisioned subprocess when the parent has colors enabled - by :user:`gaborbernat`. (:issue:`3331`)
- ``set_env`` values defined after a ``file|`` reference now correctly take precedence over values loaded from the env
  file - by :user:`gaborbernat`. (:issue:`3335`)
- The ``base`` configuration key now works correctly in TOML format (``tox.toml`` and ``pyproject.toml``), allowing
  environments to inherit from arbitrary sections defined under ``[env.*]`` - by :user:`gaborbernat`. (:issue:`3497`)
- Skip ``toxfile.py`` inline plugin when it uses hooks not available in the current tox version instead of crashing -
  this allows provisioning to upgrade tox to a version that supports those hooks - by :user:`gaborbernat`.
  (:issue:`3593`)
- ``set_env`` substitution referencing ``{envsitepackagesdir}``, ``{envbindir}``, or ``{envpython}`` for environments
  with missing interpreters now raises ``Skip`` instead of ``RuntimeError``, allowing ``skip_missing_interpreters`` to
  work correctly - by :user:`gaborbernat`. (:issue:`3597`)
- A ``setup.cfg`` without a ``[tox:tox]`` section no longer blocks discovery of ``pyproject.toml`` or ``tox.toml``
  configuration files in the same directory - by :user:`gaborbernat`. (:issue:`3602`)
- Fix pytest ``INTERNALERROR`` on Python 3.15 caused by Pygments using deprecated ``os.path.commonprefix()`` - by
  :user:`gaborbernat`. (:issue:`3733`)
- Fix ``RecursionError`` when TOML ``set_env`` contains substitutions like ``{env_site_packages_dir}`` that trigger
  config loading cycles -- the TOML loader now defers string substitution in ``set_env`` values, matching the INI
  loader's lazy resolution behavior - by :user:`gaborbernat`. (:issue:`3758`)

.. _release-4-39-0-documentation:

Documentation
-------------

- Document that interactive terminal programs (e.g., IPython) may not work correctly under tox due to the PTY-based
  output capture architecture - by :user:`gaborbernat`. (:issue:`2999`)

.. _release-4-38-0:

*********************
 4.38.0 (2026-02-17)
*********************

.. _release-4-38-0-added:

Added
-----

- Scope dependency rejection in PEP-517 package environments to only pure PEP-517 build types (``sdist``, ``wheel``,
  ``editable``), allowing non-standard package types like ``editable-legacy`` to specify dependencies - by
  :user:`rahuldevikar`. (:issue:`3731`)

.. _release-4-37-0:

*********************
 4.37.0 (2026-02-17)
*********************

.. _release-4-37-0-added:

Added
-----

- Add ``extra_setup_commands`` configuration option to run commands after dependency and package installation but before
  test commands, useful with ``--notest`` for separating setup from execution - by :user:`gaborbernat`. (:issue:`1504`)

.. _release-4-37-0-fixed:

Fixed
-----

- Set ``PIP_USER=0`` environment variable when running pip commands in virtualenvs to prevent pip from attempting
  ``--user`` installs when users have ``pip config --user`` configured globally — by :user:`gaborbernat`.
  (:issue:`3010`)
- Fix TOML env_run_base and env_pkg_base deps being clobbered when referenced with additional deps in testenv
  configuration (:issue:`3393`)
- Normalize extra names when resolving dependencies so that underscores and hyphens are treated equivalently (e.g.
  ``extras = snake_case`` now matches ``Provides-Extra: snake-case`` in wheel metadata) - by :user:`Fridayai700`.
  (:issue:`3433`)
- Fix ``setenv`` modifications to ``PATH`` being overwritten when tox environment paths are set up - by
  :user:`Fridayai700` (:issue:`3445`)
- Fix ``deps`` entries with ``~=`` version specifier being incorrectly treated as local paths instead of being passed
  through to pip - by :user:`Fridayai700`. (:issue:`3447`)
- Fix factor selection via ``TOX_FACTORS`` environment variable producing wrong results because ``append`` +
  ``nargs="+"`` actions need nested list types for proper env var conversion - by :user:`Fridayai700`. (:issue:`3557`)
- Fix custom ``install_command`` being ignored when specified in TOML configuration (``tox.toml``/``pyproject.toml``) -
  by :user:`Fridayai700`. (:issue:`3574`)
- Fix env names containing dots (e.g. ``py3.11``) losing their description in TOML configuration - by
  :user:`Fridayai700`. (:issue:`3590`)
- Run pre-commit on changelog.rst after towncrier build to ensure proper formatting before committing the release
  (:issue:`3717`)
- Fix type checker CI failure by adding ``completion`` extras to ``type`` and ``type-min`` environments so ``ty`` can
  resolve the ``argcomplete`` import - by :user:`gaborbernat`. (:issue:`3728`)

.. _release-4-37-0-documentation:

Documentation
-------------

- Restructured documentation using the Diátaxis framework to separate Tutorial, How-to guides, Reference, and
  Explanation content for better discoverability and user experience. (:issue:`3718`)

.. _release-4-36-1:

*********************
 4.36.1 (2026-02-17)
*********************

.. _release-4-36-1-fixed:

Fixed
-----

- Report TOML parse errors during config discovery instead of silently ignoring them - by :user:`rahuldevikar`.
  (:issue:`3030`)
- Adopt CPython's subprocess stream handling to fix deadlocks and improve performance when reading subprocess output
  (:issue:`3715`)

.. _release-4-36-1-documentation:

Documentation
-------------

- Add Unix man page generation and installation support using sphinx-argparse-cli - by :user:`gaborbernat`.
  (:issue:`1409`)
- Document use of Python :mod:`logging` for plugin authors in the how-to guides, covering verbosity levels, coloring,
  and best practices — by :user:`rahuldevikar`. (:issue:`3449`)
- Add architecture documentation for new contributors under the development section - by :user:`rahuldevikar`
  (:issue:`3707`)

.. _release-4-36-0:

*********************
 4.36.0 (2026-02-15)
*********************

.. _release-4-36-0-added:

Added
-----

- Allow ``skip_missing_interpreters`` to be set per environment, overriding the global setting. This enables marking
  specific environments as optional while keeping others required. (:issue:`435`)
- Add ``--fail-fast`` CLI flag and ``fail_fast`` per-environment config option to stop executing remaining environments
  when the first failure occurs - by :user:`gaborbernat`. (:issue:`578`)
- Add shell completion support for bash, zsh, and fish via :pypi:`argcomplete` - by :user:`gaborbernat` (:issue:`918`)
- Validate that configured extras exist in package metadata, raising a clear error for unknown extras - by
  :user:`gaborbernat` (:issue:`1113`)
- Add glob pattern support in ``depends`` (e.g. ``depends = py3*``) to match environments by wildcard instead of listing
  them explicitly - by :user:`gaborbernat` (:issue:`1152`)
- Add ``disallow_pass_env`` configuration option to exclude specific environment variables after ``pass_env`` glob
  expansion - by :user:`gaborbernat` (:issue:`1387`)
- Support ``file:`` URIs in ``--installpkg`` (e.g. ``--installpkg file:///path/to/pkg.whl``), including proper handling
  of percent-encoded characters - by :user:`rahuldevikar`. (:issue:`3498`)
- Add GitHub Actions workflow dispatch for release preparation as alternative to local ``tox r -e release`` command - by
  :user:`gaborbernat` (:issue:`3704`)

.. _release-4-36-0-changes:

Changes
-------

- Switch type checker from ``mypy`` to ``ty`` - by :user:`gaborbernat`. (:issue:`3685`)

.. _release-4-36-0-fixed:

Fixed
-----

- Raise an error when ``deps`` is configured on a PEP-517 packaging environment (e.g. ``.pkg``), since build
  dependencies should be specified via the ``[build-system]`` table in ``pyproject.toml`` - by :user:`rahuldevikar`
  (:issue:`3412`)
- Follow `FORCE_COLOR <https://force-color.org/>`_ recommendations: any non-empty value now enables color (previously
  only ``yes``, ``true``, or ``1`` were accepted, and other values caused a crash). Also add support for
  ``TTY_COMPATIBLE`` (``1`` forces color, ``0`` disables it) — by :user:`rahuldevikar`. (:issue:`3579`)
- Return non-zero exit code from tox config when configuration exceptions occur. (:issue:`3649`)
- Fix flaky spinner test assertion caused by timing variations on slower systems. (:issue:`3692`)

.. _release-4-36-0-documentation:

Documentation
-------------

- Document how to provide environments via ``toxfile.py`` inline plugins using ``tox_extend_envs`` and ``MemoryLoader``
  by :user:`gaborbernat`. (:issue:`828`)
- Document shell completion setup for bash, zsh, and fish in the CLI reference - by :user:`gaborbernat` (:issue:`918`)
- Document negative factor conditions and multi-factor combinations with negation in the INI configuration reference -
  by :user:`gaborbernat` (:issue:`3276`)
- Add a substitution quick reference table covering all available ``{...}`` replacement variables - by
  :user:`gaborbernat` (:issue:`3326`)
- Add TOML configuration reference with complete examples for ``tox.toml`` and ``pyproject.toml`` formats, and emphasize
  TOML as the recommended format throughout - by :user:`gaborbernat` (:issue:`3393`)
- Document the ``tox exec`` subcommand with usage examples in the how-to guides - by :user:`gaborbernat` (:issue:`3403`)
- Comprehensive documentation improvements: added how-to guides for tox exec, CI/CD, coverage, build backends, labels,
  migration, debugging, and extras; expanded plugin documentation with all hook examples and packaging guide; added env
  var handling guide, factor conditions reference, and substitution quick reference; integrated docstrfmt for consistent
  RST formatting; fixed docstring issues in source code - by :user:`gaborbernat` (:issue:`3475`)
- Update ``development.rst`` to reflect current standards: replace references to
  ``flake8``/``black``/``isort``/``pyupgrade`` with ``ruff``, remove outdated Python 2.7 compatibility note, and fix CI
  config filename - by :user:`rahuldevikar` (:issue:`3483`)
- Drop ``setup.py`` mentions from the installation page — by :user:`rahuldevikar`. (:issue:`3588`)
- Restructure documentation following the `Diataxis <https://diataxis.fr/>`_ framework: add a step-by-step tutorial
  (``getting_started.rst``), consolidate how-to recipes (``howto.rst``), refocus the user guide on conceptual
  explanation, and move plugin docs into their own ``plugins/`` subdirectory. Remove the obsolete tox 3-to-4 migration
  guide (``upgrading.rst``) and FAQ, redistributing still-relevant content into the appropriate sections. All
  configuration examples now show TOML first with INI alongside - by :user:`gaborbernat` (:issue:`3702`)

.. _release-4-35-0:

*********************
 4.35.0 (2026-02-12)
*********************

.. _release-4-35-0-added:

Added
-----

- Show ``toxfile.py`` inline plugins in ``tox --version`` output, including any ``tox_append_version_info()`` result -
  by :user:`rahuldevikar`. (:issue:`3508`)

.. _release-4-35-0-documentation:

Documentation
-------------

- Document injected environment variables (``TOX_ENV_NAME``, ``TOX_WORK_DIR``, ``TOX_ENV_DIR``, ``TOX_PACKAGE``,
  ``VIRTUAL_ENV``, ``PYTHONIOENCODING``, ``__TOX_ENVIRONMENT_VARIABLE_ORIGINAL_CI``) that tox automatically sets when
  running commands - by :user:`rahuldevikar`. (:issue:`3514`)

.. _release-4-34-1:

*********************
 4.34.1 (2026-01-09)
*********************

.. _release-4-34-1-fixed:

Fixed
-----

- Fix wheel corruption errors when the build backend updates the file in place - by :user:`gaborbernat`. (:issue:`3667`)

.. _release-4-34-0:

*********************
 4.34.0 (2026-01-08)
*********************

.. _release-4-34-0-added:

Added
-----

- Support installing extras from the current project in dependency groups. -- by :user:`czaki`. (:issue:`3561`)

.. _release-4-33-0:

*********************
 4.33.0 (2026-01-02)
*********************

.. _release-4-33-0-added:

Added
-----

- Add support for conditional ``set_env`` using PEP-496 environment markers. In INI format use ``VAR=value; marker``
  syntax, in TOML format use ``set_env.VAR = { value = "...", marker = "..." }`` -- by :user:`gaborbernat`.
  (:issue:`3663`)

.. _release-4-33-0-fixed:

Fixed
-----

- Added 'LocalAppData' to the default passed environment variables on Windows. (:issue:`3639`)

.. _release-4-33-0-documentation:

Documentation
-------------

- Sphinx is now set up to use :pypi:`sphinx-issues` for referencing GitHub issues and pull requests in the docs -- by
  :user:`webknjaz`. (:issue:`3202`)

.. _release-4-32-0:

*********************
 4.32.0 (2025-10-24)
*********************

.. _release-4-32-0-fixed:

Fixed
-----

- Expand braced range syntax in all internal sections of ``tox.ini`` (e.g. ``deps``, ``testenv``). Syntax like
  py3{10-14} can be used in those sections now. - by :user:`marcosboger` (:issue:`3571`)

.. _release-4-32-0-documentation:

Documentation
-------------

- Add Python 3.14 and 3.14t to config examples - by :user:`cclauss` (:issue:`3626`)

.. _release-4-31-0:

*********************
 4.31.0 (2025-10-09)
*********************

.. _release-4-30-3:

*********************
 4.30.3 (2025-10-02)
*********************

.. _release-4-30-3-fixed:

Fixed
-----

- Fix incorrect type annotation in ``PythonPathPackageWithDeps.__init__()`` where ``deps`` was annotated as
  ``Sequence[Package]`` but should be ``Sequence[Requirement]`` to match actual runtime usage - by
  :user:`PreistlyPython` (:issue:`3607`)
- Fix ``None`` appearing as the config filename in error output when the user's default config file is corrupt. - by
  :user:`kurtmckee` (:issue:`3611`)

.. _release-4-30-2:

*********************
 4.30.2 (2025-09-04)
*********************

.. _release-4-30-2-fixed:

Fixed
-----

- Previously, when tox ran in an automatically provisioned environment, it could hang waiting for a PEP 517 build
  backend if used in conjunction with the ``--installpkg`` option. This has been fixed by properly tearing down the
  automatically provisioned environment after the tests. - by :user:`vytas7` (:issue:`3600`)

.. _release-4-30-1:

*********************
 4.30.1 (2025-09-03)
*********************

.. _release-4-30-1-fixed:

Fixed
-----

- Prevent tox from hanging upon exit due to orphaned build threads and subprocesses when the ``--installpkg`` option is
  used with *sdist*. - by :user:`vytas7` (:issue:`3530`)

.. _release-4-30-0:

*********************
 4.30.0 (2025-09-03)
*********************

.. _release-4-30-0-added:

Added
-----

- Add ``__TOX_ENVIRONMENT_VARIABLE_ORIGINAL_CI``, which passes through the ``CI`` variable if present. This is intended
  for use by other libraries to detect if tox is running under CI. (:issue:`3442`)

.. _release-4-30-0-fixed:

Fixed
-----

- Makes the error message more clear when pyproject.toml file cannot be loaded or is missing expected keys.
  (:issue:`3578`)
- The :func:`tox_extend_envs() hook <tox.plugin.spec.tox_extend_envs>` recently added in :pr:`3591` turned out to not
  work well with ``tox run``. It was fixed internally, not to exhaust the underlying iterator on the first use. -- by
  :user:`webknjaz` (:issue:`3598`)

.. _release-4-29-0:

*********************
 4.29.0 (2025-08-29)
*********************

.. _release-4-29-0-added:

Added
-----

- A new tox life cycle event is now exposed for use via :doc:`Plugins API </plugin/index>` -- by :user:`webknjaz`. The
  corresponding hook point is :func:`tox_extend_envs <tox.plugin.spec.tox_extend_envs>`. It allows plugin authors to
  declare ephemeral environments that they can then populate through the in-memory configuration loader interface. This
  patch was made possible thanks to pair programming with :user:`gaborbernat` at PyCon US 2025. (:issue:`3510`,
  :issue:`3591`)

.. _release-4-28-4:

*********************
 4.28.4 (2025-07-31)
*********************

.. _release-4-28-4-added:

Added
-----

- Pass ssh-agent variables ``SSH_AGENT_PID`` and ``SSH_AUTH_SOCK`` in ``pass_env`` by default. - by :user:`daniilgankov`
  (:issue:`3572`)

.. _release-4-28-3:

*********************
 4.28.3 (2025-07-25)
*********************

.. _release-4-28-2:

*********************
 4.28.2 (2025-07-25)
*********************

.. _release-4-28-2-fixed:

Fixed
-----

- Don't pass in the filter argument to tar.extractall on old Python versions - by :user:`gaborbernat`. (:issue:`3568`)

.. _release-4-28-1:

*********************
 4.28.1 (2025-07-22)
*********************

.. _release-4-28-1-fixed:

Fixed
-----

- Use `tarfile.data_filter <https://docs.python.org/3/library/tarfile.html#tarfile.data_filter>`_ with ``extractall``
  only on supported Python versions:

  - ``>= 3.11.4``
  - ``>= 3.10.12`` and ``< 3.11``
  - ``>= 3.9.17`` and ``< 3.10`` by :user:`gaborbernat`. (:issue:`3565`)

.. _release-4-28-0:

*********************
 4.28.0 (2025-07-20)
*********************

.. _release-4-28-0-added:

Added
-----

- Added ``constraints`` to allow specifying constraints files for all dependencies. (:issue:`3550`)
- Allow disabling tox plugins via the ``TOX_DISABLED_EXTERNAL_PLUGINS`` environment variable - by :user:`gaborbernat`.
  (:issue:`3468`)

.. _release-4-28-0-documentation:

Documentation
-------------

- The ``min_version``/``minversion`` config option is deprecated in favor of the ``requires`` option. (:issue:`3553`)

.. _release-4-27-0:

*********************
 4.27.0 (2025-06-17)
*********************

.. _release-4-27-0-added:

Added
-----

- Add ``free_threaded`` flag to to ``"python"`` entries in json output of ``--result-json``. (:issue:`3534`)

.. _release-4-27-0-fixed:

Fixed
-----

- Fix dependency-group name normalization. (:issue:`3539`)
- Improves logging of environment variables by sorting them by key and redacting the values for the ones that are likely
  to contain secrets. (:issue:`3542`)

.. _release-4-26-0:

*********************
 4.26.0 (2025-05-13)
*********************

.. _release-4-26-0-added:

Added
-----

- Add support for free-threaded python builds. Factors like ``py313t`` will only pick builds with the GIL disabled while
  factors without trailing ``t`` will only pick builds without no-GIL support. (:issue:`3391`)
- Drop support for EOL Python 3.8. (:issue:`3527`)

.. _release-4-26-0-fixed:

Fixed
-----

- Fix a regression issue related to inability to use ``file|`` substitution option in nested ``set_env`` sections of
  ``ini`` configurations since tox4 update. (:issue:`2435`)
- Fix ``TypeError`` for ``HelpFormatter`` with Python 3.14 (:issue:`3523`)

.. _release-4-25-0:

*********************
 4.25.0 (2025-03-27)
*********************

.. _release-4-25-0-added:

Added
-----

- Add support for number ranges in generative environments, more details :ref:`here <generative-environment-list>`. - by
  :user:`mimre25` (:issue:`3502`)

.. _release-4-25-0-fixed:

Fixed
-----

- Make tox tests pass with Python 3.14.0a6 - by :user:`hroncok` (:issue:`3500`)

.. _release-4-24-2:

*********************
 4.24.2 (2025-03-07)
*********************

.. _release-4-24-2-fixed:

Fixed
-----

- multiple source_type supports for the same filename. Like pyproject.toml can be load by both TomlPyProject &
  LegacyToml (:issue:`3117`)
- Support ``set_env = { file = "conf{/}local.env"}`` for TOML format - by :user:`juditnovak`. (:issue:`3474`)
- fix example on the docs (:issue:`3480`)
- - ``--parallel-no-spinner`` now respects max CPU set by ``--parallel N`` (:issue:`3495`)

.. _release-4-24-2-documentation:

Documentation
-------------

- Updates the documentation for ``os.environ['KEY']`` when the variable does not exist - by :user:`jugmac00`.
  (:issue:`3456`)

.. _release-4-24-1:

*********************
 4.24.1 (2025-01-21)
*********************

.. _release-4-24-0:

*********************
 4.24.0 (2025-01-21)
*********************

.. _release-4-24-0-added:

Added
-----

- Add a ``schema`` command to produce a JSON Schema for tox and the current plugins. - by :user:`henryiii`
  (:issue:`3446`)

.. _release-4-24-0-fixed:

Fixed
-----

- Log exception name when subprocess execution produces one. - by :user:`ssbarnea` (:issue:`3450`)

.. _release-4-24-0-documentation:

Documentation
-------------

- Fix typo in ``docs/config.rst`` from ``{}`` to ``{:}``. - by :user:`wooshaun53` (:issue:`3424`)
- Pass ``NIX_LD`` and ``NIX_LD_LIBRARY_PATH`` variables by default in ``pass_env`` to make generic binaries work under
  Nix/NixOS. - by :user:`albertodonato` (:issue:`3425`)

.. _release-4-23-2:

*********************
 4.23.2 (2024-10-22)
*********************

.. _release-4-23-1:

*********************
 4.23.1 (2024-10-21)
*********************

.. _release-4-23-1-documentation:

Documentation
-------------

- Fix bad example in documentation for dependency groups - by :user:`gaborbernat`. (:issue:`3240`)

.. _release-4-23-0:

*********************
 4.23.0 (2024-10-16)
*********************

.. _release-4-23-0-added:

Added
-----

- Add ``NETRC`` to the list of environment variables always passed through. (:issue:`3410`)

.. _release-4-23-0-documentation:

Documentation
-------------

- replace ``[tool.pyproject]`` and ``[tool.tox.pyproject]`` with ``[tool.tox]`` in config.rst (:issue:`3411`)

.. _release-4-22-0:

*********************
 4.22.0 (2024-10-15)
*********************

.. _release-4-22-0-added:

Added
-----

- Implement dependency group support as defined in :PEP:`735` - see :ref:`dependency_groups` - by :user:`gaborbernat`.
  (:issue:`3408`)

.. _release-4-21-2:

*********************
 4.21.2 (2024-10-03)
*********************

.. _release-4-21-2-fixed:

Fixed
-----

- Include ``tox.toml`` in sdist archives to fix test failures resulting from its lack. - by :user:`mgorny`
  (:issue:`3389`)

.. _release-4-21-1:

*********************
 4.21.1 (2024-10-02)
*********************

.. _release-4-21-1-fixed:

Fixed
-----

- Fix error when using ``requires`` within a TOML configuration file - by :user:`gaborbernat`. (:issue:`3386`)
- Fix error when using ``deps`` within a TOML configuration file - by :user:`gaborbernat`. (:issue:`3387`)
- Multiple fixes for the TOML configuration by :user:`gaborbernat`.:

  - Do not fail when there is an empty command within ``commands``.
  - Allow references for ``set_env`` by accepting list of dictionaries for it.
  - Do not try to be smart about reference unrolling, instead allow the user to control it via the ``extend`` flag,
    available both for ``posargs`` and ``ref`` replacements.
  - The ``ref`` replacements ``raw`` key has been renamed to ``of``. (:issue:`3388`)

.. _release-4-21-0:

*********************
 4.21.0 (2024-09-30)
*********************

.. _release-4-21-0-added:

Added
-----

- Native TOML configuration support - by :user:`gaborbernat`. (:issue:`999`)

.. _release-4-21-0-documentation:

Documentation
-------------

- Update Loader docs - by :user:ziima (:issue:`3352`)

.. _release-4-20-0:

*********************
 4.20.0 (2024-09-18)
*********************

.. _release-4-20-0-added:

Added
-----

- Separate the list dependencies functionality to a separate abstract class allowing code reuse in plugins (such as
  ``tox-uv``) - by :gaborbernat`. (:issue:`3347`)

.. _release-4-19-0:

*********************
 4.19.0 (2024-09-17)
*********************

.. _release-4-19-0-added:

Added
-----

- Support ``pypy-<major>.<minor>`` environment names for PyPy environments - by :user:`gaborbernat`. (:issue:`3346`)

.. _release-4-18-1:

*********************
 4.18.1 (2024-09-07)
*********************

.. _release-4-18-1-fixed:

Fixed
-----

- Fix and test the string spec for the ``sys.executable`` interpreter (introduced in :pr:`3325`) - by :user:`hroncok`
  (:issue:`3327`)

.. _release-4-18-1-documentation:

Documentation
-------------

- Changes the ``tox_env_teardown`` docstring to explain the hook is called after a tox env was teared down.
  (:issue:`3305`)

.. _release-4-18-0:

*********************
 4.18.0 (2024-08-13)
*********************

.. _release-4-18-0-added:

Added
-----

- Suppress spinner in parallel runs in CI - by :user:`ziima`. (:issue:`3318`)

.. _release-4-18-0-fixed:

Fixed
-----

- Boost temporary directories cleanup in tests - by :user:`ziima`. (:issue:`3278`)
- Fix absolute base python paths conflicting - by :user:`gaborbernat`. (:issue:`3325`)

.. _release-4-17-1:

*********************
 4.17.1 (2024-08-07)
*********************

.. _release-4-17-1-fixed:

Fixed
-----

- Support for running ``-e <major>.<minor>`` has been lost, fixing it - by :user:`gaborbernat`. (:issue:`2849`)
- ``base_python`` now accepts absolute paths to interpreter executable - by :user:`paveldikov`. (:issue:`3191`)

.. _release-4-17-0:

*********************
 4.17.0 (2024-08-05)
*********************

.. _release-4-17-0-added:

Added
-----

- Add ``graalpy`` prefix as a supported base python (:issue:`3312`)
- Add :ref:`on_platform` core configuration holding the tox platform and do not install package when exec an environment
  by :user:`gaborbernat`. (:issue:`3315`)

.. _release-4-17-0-fixed:

Fixed
-----

- Add table with default environment variables per OS (:issue:`2753`)

.. _release-4-16-0:

*********************
 4.16.0 (2024-07-02)
*********************

.. _release-4-16-0-fixed:

Fixed
-----

- - Add ``windir`` to the default list of Windows ``pass_env`` environment variables. - by :user:`kurtmckee`
    (:issue:`3302`)

.. _release-4-16-0-documentation:

Documentation
-------------

- - Fix typo in configuration example and fix broken link to code style guide. - by :user:`srenfo` (:issue:`3297`)

.. _release-4-15-1:

*********************
 4.15.1 (2024-06-05)
*********************

.. _release-4-15-1-added:

Added
-----

- Fix ``skip_missing_interpreters`` option for ``package = wheel`` (:issue:`3269`)

.. _release-4-15-1-fixed:

Fixed
-----

- Fix section substitution with setenv. (:issue:`3262`)
- Allow ``ConfigSet.add_config`` to receive parameterized generics for ``of_type``. (:issue:`3288`)

.. _release-4-15-0:

*********************
 4.15.0 (2024-04-26)
*********************

.. _release-4-15-0-added:

Added
-----

- Add support for multiple appending override options (-x, --override) on command line - by :user:`amitschang`.
  (:issue:`3261`)
- Add support for inverting exit code success criteria using bang (!) (:issue:`3271`)

.. _release-4-15-0-fixed:

Fixed
-----

- Fix issue that the leading character ``c`` was dropped from packages in constraints files - by :user:`jugmac00`.
  (:issue:`3247`)
- Allow appending to ``deps`` with ``--override testenv.deps+=foo`` - by :user:`stefanor`. (:issue:`3256`)
- Fix non-existing branch ``rewrite`` in the documentation to ``main``. (:issue:`3257`)
- Update test typing for build 1.2.0, which has an explicit ``Distribution`` type - by :user:`stefanor`. (:issue:`3260`)
- Fix broken input parsing for ``--discover`` flag. - by :user:`mimre25` (:issue:`3272`)

.. _release-4-15-0-documentation:

Documentation
-------------

- Rephrase ``--discover`` flag's description to avoid confusion between paths and executables. - by :user:`mimre25`
  (:issue:`3274`)

.. _release-4-14-2:

*********************
 4.14.2 (2024-03-22)
*********************

.. _release-4-14-2-fixed:

Fixed
-----

- Add provision arguments to ToxParser to fix crash when provisioning new tox environment without list-dependencies by
  :user:`seyidaniels` (:issue:`3190`)

.. _release-4-14-2-documentation:

Documentation
-------------

- Removed unused line from the ``fresh_subprocess`` documentation. (:issue:`3241`)

.. _release-4-14-1:

*********************
 4.14.1 (2024-03-06)
*********************

.. _release-4-14-1-fixed:

Fixed
-----

- Fix crash with fresh subprocess, if the build backend is setuptools automatically enable fresh subprocesses for build
  backend calls - by :user:`gaborbernat`. (:issue:`3235`)

.. _release-4-14-0:

*********************
 4.14.0 (2024-03-05)
*********************

.. _release-4-14-0-added:

Added
-----

- Support enabling fresh subprocess for packaging build backends via :ref:`fresh_subprocess` - by :user:`gaborbernat`.
  (:issue:`3227`)
- Allow plugins attaching additional information to ``--version`` via ``tox_append_version_info`` method in the plugin
  module - by :user:`gaborbernat`. (:issue:`3234`)

.. _release-4-13-0:

*********************
 4.13.0 (2024-02-16)
*********************

.. _release-4-13-0-added:

Added
-----

- Extract virtual environment packaging code to its own base class not tied to ``virtualenv`` - by :user:`gaborbernat`.
  (:issue:`3221`)

.. _release-4-13-0-documentation:

Documentation
-------------

- Documented usage of ``pytest`` with ``tox run-parallel`` - by :user:`faph`. (:issue:`3187`)
- Configuration: state in config directive sections their ini file sections - by :user:`0cjs`. (:issue:`3194`)
- Development: summarize important points experienced developers need to know - by :user:`0cjs`. (:issue:`3197`)

.. _release-4-12-1:

*********************
 4.12.1 (2024-01-16)
*********************

.. _release-4-12-1-fixed:

Fixed
-----

- Fixed bug where running with --installpkg and multiple envs could not clean up between tests (:issue:`3165`)

.. _release-4-12-0:

*********************
 4.12.0 (2024-01-11)
*********************

.. _release-4-12-0-added:

Added
-----

- Always pass ``FORCE_COLOR`` and ``NO_COLOR`` to the environment (:issue:`3172`)

.. _release-4-12-0-fixed:

Fixed
-----

- ``--parallel-no-spinner`` flag now implies ``--parallel`` (:issue:`3158`)

.. _release-4-12-0-documentation:

Documentation
-------------

- -Fix ``open an issue`` link in development.rst (:issue:`3179`)

.. _release-4-11-4:

*********************
 4.11.4 (2023-11-27)
*********************

.. _release-4-11-4-fixed:

Fixed
-----

- Fix terminal size of tox subcommands (fixes ipython, ipdb, prompt_toolkit, ...). (:issue:`2999`)
- Fix ``quickstart`` command from requiring ``root`` positional argument (:issue:`3084`)
- Added 'AppData' to the default passed environment variables on Windows. (:issue:`3151`)

.. _release-4-11-4-documentation:

Documentation
-------------

- Fix default value for ``install_command`` - by :user:`hashar`. (:issue:`3126`)
- Fix default value for ``base_python`` - by :user:`rpatterson`. (:issue:`3156`)

.. _release-4-11-3:

*********************
 4.11.3 (2023-09-08)
*********************

.. _release-4-11-3-fixed:

Fixed
-----

- Handle ``FileNotFoundError`` when the ``base_python`` interpreter doesn't exist (:issue:`3105`)

.. _release-4-11-3-documentation:

Documentation
-------------

- Explain how plugins are registered and discovered - by :user:`hashar`. (:issue:`3116`)

.. _release-4-11-2:

*********************
 4.11.2 (2023-09-07)
*********************

.. _release-4-11-2-fixed:

Fixed
-----

- Fix bug in ``config.rst`` by removing stray colons left over from (:issue:`3111`) - by :user:`posita`. (:issue:`3118`)
- Provide example to make CLI help more helpful for ``-x``/``--override`` - by :user:`posita`. (:issue:`3119`)

.. _release-4-11-2-documentation:

Documentation
-------------

- Fix typos discovered by codespell - by :user:`cclauss`. (:issue:`3113`)

.. _release-4-11-1:

*********************
 4.11.1 (2023-09-01)
*********************

.. _release-4-11-1-fixed:

Fixed
-----

- Allow passing in multiple overrides using the ``;`` character and fix ``,`` being used as splitting values - by
  :user:`gaborbernat`. (:issue:`3112`)

.. _release-4-11-0:

*********************
 4.11.0 (2023-08-29)
*********************

.. _release-4-11-0-added:

Added
-----

- Add support for setting build backend ``config_settings`` in the configuration file - by :user:`gaborbernat`.
  (:issue:`3090`)

.. _release-4-10-0:

*********************
 4.10.0 (2023-08-21)
*********************

.. _release-4-10-0-added:

Added
-----

- Change accepted environment name rule: must be made up of factors defined in configuration or match regex
  ``(pypy|py|cython|)((\d(\.\d+(\.\d+)?)?)|\d+)?``. If an environment name does not match this fail, and if a close
  match found suggest that to the user. (:issue:`3099`)

.. _release-4-10-0-fixed:

Fixed
-----

- ``--override foo+=bar`` appending syntax will now work correctly when ``foo`` wasn't defined in ``tox.ini``.
  (:issue:`3100`)

.. _release-4-9-0:

********************
 4.9.0 (2023-08-16)
********************

.. _release-4-9-0-added:

Added
-----

- Disallow command line environments which are not explicitly specified in the config file - by :user:`tjsmart`.
  (:issue:`2858`)

.. _release-4-8-0:

********************
 4.8.0 (2023-08-12)
********************

.. _release-4-8-0-added:

Added
-----

- ``--override`` can now take options in the form of ``foo+=bar`` which will append ``bar`` to the end of an existing
  list/dict, rather than replacing it. (:issue:`3087`)

.. _release-4-7-0:

********************
 4.7.0 (2023-08-08)
********************

.. _release-4-7-0-added:

Added
-----

- Make ``--hashseed`` default to ``PYTHONHASHSEED``, if defined - by :user:`paravoid`. The main motivation for this is
  to able to set the hash seed when building the documentation with ``tox -e docs``, and thus avoid embedding a random
  value in the tox documentation for --help. This caused documentation builds to fail to build reproducibly.
  (:issue:`2942`)

.. _release-4-7-0-fixed:

Fixed
-----

- Update a regular expression in tests to match the exception message in both Python 3.12 and older. (:issue:`3065`)

.. _release-4-7-0-documentation:

Documentation
-------------

- Fix broken links - by :user:`gaborbernat`. (:issue:`3072`)

.. _release-4-6-4:

********************
 4.6.4 (2023-07-06)
********************

.. _release-4-6-4-fixed:

Fixed
-----

- Fix hang and zombie process on interrupt (CTRL-C). (:issue:`3056`)

.. _release-4-6-3:

********************
 4.6.3 (2023-06-19)
********************

.. _release-4-6-3-fixed:

Fixed
-----

- Ensure that ``get_requires_for_build_wheel`` is called before ``prepare_metadata_for_build_wheel``, and
  ``get_requires_for_build_editable`` is called before ``prepare_metadata_for_build_editable`` - by :user:`abravalheri`.
  (:issue:`3043`)

.. _release-4-6-3-documentation:

Documentation
-------------

- Linked environment variable substitutions docs in ``set_env`` and ``pass_env`` config docs. (:issue:`3039`)

.. _release-4-6-2:

********************
 4.6.2 (2023-06-16)
********************

.. _release-4-6-2-fixed:

Fixed
-----

- Avoid cache collision between editable wheel build and normal wheel build -- by :user:`f3flight`. (:issue:`3035`)

.. _release-4-6-1:

********************
 4.6.1 (2023-06-15)
********************

.. _release-4-6-0:

********************
 4.6.0 (2023-06-05)
********************

.. _release-4-6-0-added:

Added
-----

- Added ``--list-dependencies`` and ``--no-list-dependencies`` CLI parameters. If unspecified, defaults to listing when
  in CI, but not otherwise. (:issue:`3024`)

.. _release-4-5-2:

********************
 4.5.2 (2023-05-27)
********************

.. _release-4-5-2-added:

Added
-----

- Add 3.12 support by :user:`gaborbernat` in https://github.com/tox-dev/tox/pull/2998

.. _release-4-5-2-fixed:

Fixed
-----

- fix legacy ``tox --devenv venv`` by :user:`asottile` in https://github.com/tox-dev/tox/pull/3013
- Fix legacy devenv by :user:`gaborbernat` in https://github.com/tox-dev/tox/pull/3019

.. _release-4-5-1-1:

**********************
 4.5.1.1 (2023-08-31)
**********************

.. _release-4-5-1:

********************
 4.5.1 (2023-05-25)
********************

.. _release-4-5-1-fixed:

Fixed
-----

- Fix ``tox --devenv venv`` invocation without ``-e`` - by :user:`asottile`. (:issue:`2925`)

.. _release-4-5-0:

********************
 4.5.0 (2023-04-24)
********************

.. _release-4-5-0-added:

Added
-----

- When run with verbosity=1, the per-step timing summaries are suppressed at the end of the run. Thanks to
  :user:`nedbat` at the PyCon 2023 sprints. (:issue:`2891`)

.. _release-4-5-0-documentation:

Documentation
-------------

- Add FAQ entry on how to test EOL Python versions by :user:`jugmac00`. (:issue:`2989`)

.. _release-4-4-12:

*********************
 4.4.12 (2023-04-13)
*********************

.. _release-4-4-12-fixed:

Fixed
-----

- Avoid race conditions in tests using the ``demo_pkg_inline`` fixture. (:issue:`2985`)

.. _release-4-4-11:

*********************
 4.4.11 (2023-04-05)
*********************

.. _release-4-4-11-fixed:

Fixed
-----

- Fixed an issue where a tox plugin couldn't change the value of ``tox_root``. (:issue:`2966`)

.. _release-4-4-10:

*********************
 4.4.10 (2023-04-05)
*********************

.. _release-4-4-10-fixed:

Fixed
-----

- Fix issue where ``work_dir`` was not correctly including ``tox_root`` for test runs. (:issue:`2933`)

.. _release-4-4-9:

********************
 4.4.9 (2023-04-05)
********************

.. _release-4-4-9-fixed:

Fixed
-----

- Instead of raising ``UnicodeDecodeError`` when command output includes non-utf-8 bytes, ``tox`` will now use
  ``surrogateescape`` error handling to convert the unrecognized bytes to escape sequences according to :PEP:`383` - by
  :user:`masenf`. (:issue:`2969`)

.. _release-4-4-9-documentation:

Documentation
-------------

- Document running tox within a Docker container. (:issue:`1035`)
- Added python version 3.11 to ``installation.rst``. (:issue:`2964`)

.. _release-4-4-8:

********************
 4.4.8 (2023-03-26)
********************

.. _release-4-4-8-fixed:

Fixed
-----

- ``tox.ini`` is now included in source distributions in order to make all tests pass. (:issue:`2939`)
- Fix ``--index-url`` and ``--find-links`` being used together in ``requirements.txt`` files. (:issue:`2959`)

.. _release-4-4-7:

********************
 4.4.7 (2023-03-12)
********************

.. _release-4-4-7-documentation:

Documentation
-------------

- docs(config): fix temp_dir default value by :user:`thecesrom` in https://github.com/tox-dev/tox/pull/2932
- docs: set html_last_updated_fmt to format string by :user:`paravoid` in https://github.com/tox-dev/tox/pull/2937

.. _release-4-4-6:

********************
 4.4.6 (2023-02-21)
********************

.. _release-4-4-6-fixed:

Fixed
-----

- Plugins are now able to access tox.ini config sections using a custom prefix with the same suffix / name as a tox
  ``testenv`` - by :user:`masenf` (:issue:`2926`)

.. _release-4-4-5:

********************
 4.4.5 (2023-02-07)
********************

.. _release-4-4-5-fixed:

Fixed
-----

- Ignore labels when tox will provision a runtime environment (``.tox``) so that environment configurations which depend
  on provisioned plugins or specific tox versions are not accessed in the outer tox process where the configuration
  would be invalid - by :user:`masenf`. (:issue:`2916`)

.. _release-4-4-4:

********************
 4.4.4 (2023-01-31)
********************

.. _release-4-4-4-fixed:

Fixed
-----

- Forward ``HOME`` by default - by :user:`gschaffner`. (:issue:`2702`)

.. _release-4-4-3:

********************
 4.4.3 (2023-01-30)
********************

.. _release-4-4-3-fixed:

Fixed
-----

- Tox will now expand self-referential extras discovered in package deps to respect local modifications to package
  metadata. This allows a package extra to explicitly depend on another package extra, which previously only worked with
  non-static metadata - by :user:`masenf`. (:issue:`2904`)

.. _release-4-4-2:

********************
 4.4.2 (2023-01-25)
********************

.. _release-4-4-2-fixed:

Fixed
-----

- Allow the user configuration file (default ``<appdir>/tox/config.ini``) to be overridden via the
  ``TOX_USER_CONFIG_FILE`` environment variable. Previously tox was looking at the ``TOX_CONFIG_FILE`` to override the
  user configuration, however that environment variable is already used to override the main configuration - by
  :user:`masenf`. (:issue:`2890`)

.. _release-4-4-1:

********************
 4.4.1 (2023-01-25)
********************

.. _release-4-4-1-fixed:

Fixed
-----

- In tox 4.4.0 ``constrain_package_deps`` was introduced with a default value of ``True``. This has been changed back to
  ``False``, which restores the original behavior of tox 4.3.5 - by :user:`masenf`. (:issue:`2897`)

.. _release-4-4-0:

********************
 4.4.0 (2023-01-25)
********************

.. _release-4-4-0-added:

Added
-----

- Test environments now recognize boolean config keys ``constrain_package_deps`` (default=true) and
  ``use_frozen_constraints`` (default=false), which control how tox generates and applies constraints files when
  performing ``install_package_deps``. If ``constrain_package_deps`` is true (default), then tox will write out
  ``{env_dir}{/}constraints.txt`` and pass it to ``pip`` during ``install_package_deps``. If ``use_frozen_constraints``
  is false (default), the constraints will be taken from the specifications listed under ``deps`` (and inside any
  requirements or constraints file referenced in ``deps``). Otherwise, ``list_dependencies_command`` (``pip freeze``) is
  used to enumerate exact package specifications which will be written to the constraints file. In previous releases,
  conflicting package dependencies would silently override the ``deps`` named in the configuration, resulting in test
  runs against unexpected dependency versions, particularly when using tox factors to explicitly test with different
  versions of dependencies - by :user:`masenf`. (:issue:`2386`)

.. _release-4-4-0-fixed:

Fixed
-----

- When parsing command lines, use ``shlex(..., posix=True)``, even on windows platforms, since non-POSIX mode does not
  handle escape characters and quoting like a shell would. This improves cross-platform configurations without hacks or
  esoteric quoting. To make this transition easier, on Windows, the backslash path separator will not treated as an
  escape character unless it precedes a quote, whitespace, or another backslash character. This allows paths to mostly
  be written in single or double backslash style. Note that **double-backslash will no longer be escaped to a single
  backslash in substitutions**, instead the double backslash will be consumed as part of command splitting, on either
  posix or windows platforms. In some instances superfluous double or single quote characters may be stripped from arg
  arrays in ways that do not occur in the default windows ``cmd.exe`` shell - by :user:`masenf`. (:issue:`2635`)

.. _release-4-4-0-documentation:

Documentation
-------------

- Add information when command from ``list_dependencies_command`` configuration option is used. (:issue:`2883`)

.. _release-4-3-5:

********************
 4.3.5 (2023-01-18)
********************

.. _release-4-3-5-fixed:

Fixed
-----

- When building a ``wheel`` or ``editable`` package with a PEP 517 backend, no longer pass an empty
  ``metadata_directory`` to the backend ``build_wheel`` or ``build_editable`` endpoint. Some backends, such as PDM and
  poetry, will not generate package metadata in the presence of a ``metadata_directory``, even if it is empty. Prior to
  this change, attempting to install a wheel created by tox using PDM or poetry would return an error like "There is no
  item named 'my-package.0.1.dist-info/WHEEL' in the archive" - by :user:`masenf`. (:issue:`2880`)

.. _release-4-3-4:

********************
 4.3.4 (2023-01-17)
********************

.. _release-4-3-4-fixed:

Fixed
-----

- When executing via the provisioning environment (``.tox`` by default), run ``tox`` in working directory of the parent
  process. Prior to this change (from tox 4.0.0), the provisioned ``tox`` would execute with ``{tox_root}`` as the
  working directory, which breaks when a relative path is passed to ``-c`` or ``--conf`` and ``tox`` is executed in a
  working directory other than ``{tox_root}`` - by :user:`masenf`. (:issue:`2876`)

.. _release-4-3-3:

********************
 4.3.3 (2023-01-16)
********************

.. _release-4-3-3-fixed:

Fixed
-----

- The provision environment (``.tox``) will never inherit from ``testenv``. During provisioning, other test environments
  are not processed, allowing the use of keys and values that may be registered by later tox version or provisioned
  plugins - by :user:`masenf`. (:issue:`2862`)

.. _release-4-3-2:

********************
 4.3.2 (2023-01-16)
********************

.. _release-4-3-2-fixed:

Fixed
-----

- Fix regression introduced in 4.3.0 which occurred when a substitution expression for an environment variable that had
  previously been substituted appears in the ini file after a substitution expression for a different environment
  variable. This situation erroneously resulted in an exception about "circular chain between set" of those variables -
  by :user:`masenf`. (:issue:`2869`)

.. _release-4-3-1:

********************
 4.3.1 (2023-01-15)
********************

.. _release-4-3-1-fixed:

Fixed
-----

- Fix regression introduced in 4.3.0 by expanding substitution expressions (``{...}``) that result from a previous
  subsitution's replacement value (up to 100 times). Note that recursive expansion is strictly depth-first; no
  replacement value will ever affect adjacent characters nor will expansion ever occur over the result of more than one
  replacement - by :user:`masenf`. (:issue:`2863`)

.. _release-4-3-0:

********************
 4.3.0 (2023-01-15)
********************

.. _release-4-3-0-added:

Added
-----

- Rewrite substitution replacement parser - by :user:`masenf`

  - ``\`` acts as a proper escape for ``\`` in ini-style substitutions
  - The resulting value of a substitution is no longer reprocessed in the context of the broader string. (Prior to this
    change, ini-values were repeatedly re-substituted until the expression no longer had modifications)
  - Migrate and update "Substitutions" section of Configuration page from v3 docs.
  - ``find_replace_part`` is removed from ``tox.config.loader.ini.replace``
  - New names exported from ``tox.config.loader.ini.replace``: - ``find_replace_expr`` - ``MatchArg`` - ``MatchError`` -
    ``MatchExpression`` - Note: the API for ``replace`` itself is unchanged. (:issue:`2732`)

- Improved documentation for factors and test env names - by :user:`stephenfin`. (:issue:`2852`)

.. _release-4-2-8:

********************
 4.2.8 (2023-01-11)
********************

.. _release-4-2-8-fixed:

Fixed
-----

- Allow using package names with env markers for pip's ``--no-binary`` and ``--only-binary`` options - by :user:`q0w`.
  (:issue:`2814`)

.. _release-4-2-7:

********************
 4.2.7 (2023-01-11)
********************

.. _release-4-2-7-fixed:

Fixed
-----

- A testenv with multiple factors, one of which conflicts with a ``base_python`` setting in ``tox.ini``, will now use
  the correct Python interpreter version - by :user:`stephenfin`. (:issue:`2838`)
- Explicitly list ``wheel`` as requirement for the tests, as some of the tests error without it. (:issue:`2843`)
- tox has reverted support for Python factors that include PATCH release info (e.g. ``py3.10.1``), build architecture
  (e.g. ``pypy3-64``) or do not define a ``py`` prefix or other supported prefix (e.g. ``3.10``). These complex factors
  were initially supported with the release of tox 4.0 but has proven complicated to support. Instead, the simple
  factors supported by tox 3 e.g. (``py310``, ``pypy3``) or period-separated equivalent (``py3.10``) introduced in tox 4
  should be used. Users who wish to specify more specific Python version information should configure the
  :ref:`base_python` setting - by :user:`stephenfin`. (:issue:`2848`)

.. _release-4-2-6:

********************
 4.2.6 (2023-01-06)
********************

.. _release-4-2-6-fixed:

Fixed
-----

- Handle properly pip ``--no-binary`` / ``--only-binary`` options in requirements.txt format files. (:issue:`2814`)

.. _release-4-2-5:

********************
 4.2.5 (2023-01-06)
********************

.. _release-4-2-5-fixed:

Fixed
-----

- The combination of ``usedevelop = true`` and ``--skip-missing-interpreters=false`` will no longer fail for
  environments that were *not* invoked - by :user:`stephenfin`. (:issue:`2811`)
- Fix an attribute error when ``use_develop = true`` is set and an unsupported interpreter version is requested - by
  :user:`stephenfin`. (:issue:`2826`)
- tox returns a non-zero error code if all envs are skipped. It will now correctly do this if only a single env was
  requested and this was skipped - by :user:`stephenfin`. (:issue:`2827`)

.. _release-4-2-4:

********************
 4.2.4 (2023-01-05)
********************

.. _release-4-2-4-fixed:

Fixed
-----

- Setting ``[testenv] basepython = python3`` will no longer override the Python interpreter version requested by a
  factor, such as ``py311`` - by :user:`stephenfin`. (:issue:`2754`)
- Also accept tab after colon before factor filter expansion - by :user:`pdecat`. (:issue:`2823`)

.. _release-4-2-3:

********************
 4.2.3 (2023-01-04)
********************

.. _release-4-2-3-fixed:

Fixed
-----

- ``devenv`` does not respect the specified path when the package is a wheel file - by :user:`gaborbernat`.
  (:issue:`2815`)
- Require space after colon before factor filter expansion, unless it is the last character of the line - by
  :user:`pdecat`. (:issue:`2822`)

.. _release-4-2-2:

********************
 4.2.2 (2023-01-04)
********************

.. _release-4-2-2-fixed:

Fixed
-----

- Add ``CC``, ``CFLAGS``, ``CCSHARED``, ``CXX``, ``CPPFLAGS``, ``LDFLAGS``, ``PKG_CONFIG`` and
  ``PKG_CONFIG_SYSROOT_DIR`` to the default passed through environment variables list as these are needed for building
  various C-extensions - by :user:`gaborbernat`. (:issue:`2818`)

.. _release-4-2-1:

********************
 4.2.1 (2023-01-03)
********************

.. _release-4-2-1-fixed:

Fixed
-----

- Fix extracting extras from markers with more than 2 extras in an or chain - by :user:`dconathan`. (:issue:`2791`)

.. _release-4-2-0:

********************
 4.2.0 (2023-01-03)
********************

.. _release-4-2-0-added:

Added
-----

- Packaging environments now inherit from the ``pkgenv`` section, allowing to set all your packaging options in one
  place, and support the ``deps`` key to set additional dependencies that will be installed after ``pyproject.toml``
  static ``requires`` but before backends dynamic requires - by :user:`gaborbernat`. (:issue:`2543`)

.. _release-4-2-0-documentation:

Documentation
-------------

- Document breaking changes with tox 4 and packaging environments - by :user:`gaborbernat`. (:issue:`2543`)
- Document how to handle environments whose names match ``tox`` subcommands - by :user:`sirosen`. (:issue:`2728`)

.. _release-4-1-3:

********************
 4.1.3 (2023-01-02)
********************

.. _release-4-1-3-fixed:

Fixed
-----

- Reuse package_env with ``--installpkg`` - by :user:`q0w`. (:issue:`2442`)
- Fail more gracefully when pip :ref:`install_command` is empty - by :user:`jayaddison`. (:issue:`2695`)

.. _release-4-1-3-documentation:

Documentation
-------------

- Add breaking-change documentation for empty ``install_command`` values - by :user:`jayaddison`. (:issue:`2695`)

.. _release-4-1-2:

********************
 4.1.2 (2022-12-30)
********************

.. _release-4-1-2-fixed:

Fixed
-----

- Fix ``--skip-missing-interpreters`` behavior - by :user:`q0w`. (:issue:`2649`)
- Restore tox 3 behavior of showing the output of pip freeze, however now only active when running inside a CI
  environment - by :user:`gaborbernat`. (:issue:`2685`)
- Fix extracting extras from markers with many extras - by :user:`q0w`. (:issue:`2791`)

.. _release-4-1-1:

********************
 4.1.1 (2022-12-29)
********************

.. _release-4-1-1-fixed:

Fixed
-----

- Fix logging error with emoji in git branch name. (:issue:`2768`)

.. _release-4-1-1-documentation:

Documentation
-------------

- Add faq entry about reuse of environments - by :user:`jugmac00`. (:issue:`2788`)

.. _release-4-1-0:

********************
 4.1.0 (2022-12-29)
********************

.. _release-4-1-0-added:

Added
-----

- ``-f`` can be used multiple times and on hyphenated factors (e.g. ``-f py311-django -f py39``) - by :user:`sirosen`.
  (:issue:`2766`)

.. _release-4-1-0-documentation:

Documentation
-------------

- Fix a grammatical typo in docs/user_guide.rst. (:issue:`2787`)

.. _release-4-0-19:

*********************
 4.0.19 (2022-12-28)
*********************

.. _release-4-0-19-fixed:

Fixed
-----

- Create temp_dir if not exists - by :user:`q0w`. (:issue:`2770`)

.. _release-4-0-18:

*********************
 4.0.18 (2022-12-26)
*********************

.. _release-4-0-18-fixed:

Fixed
-----

- Strip leading and trailing whitespace when parsing elements in requirement files - by :user:`gaborbernat`.
  (:issue:`2773`)

.. _release-4-0-17:

*********************
 4.0.17 (2022-12-25)
*********************

.. _release-4-0-17-added:

Added
-----

- Suppress a report output when verbosity = 0. (:issue:`2697`)

.. _release-4-0-17-fixed:

Fixed
-----

- Fix ``--sdistonly`` behavior. (:issue:`2653`)
- Override toxworkdir with --workdir. (:issue:`2654`)

.. _release-4-0-16:

*********************
 4.0.16 (2022-12-20)
*********************

.. _release-4-0-16-fixed:

Fixed
-----

- Fix :ref:`change_dir` is relative to current working directory rather than to the :ref:`tox_root` when using the
  ``-c`` argument to locate the ``tox.ini`` file - by :user:`gaborbernat`. (:issue:`2619`)

.. _release-4-0-15:

*********************
 4.0.15 (2022-12-19)
*********************

.. _release-4-0-15-fixed:

Fixed
-----

- Fix tox auto-provisioning not working and relax :ref:`min_version` default from ``4.0`` to no version constraint - by
  :user:`gaborbernat`. (:issue:`2634`)
- Fix assertion in ``test_result_json_sequential`` when interpreter ``_base_executable`` is a hardlink (macOS homebrew)
  by :user:`masenf`. (:issue:`2720`)
- Complex negative factor filters not working - by :user:`gaborbernat`. (:issue:`2747`)

.. _release-4-0-14:

*********************
 4.0.14 (2022-12-18)
*********************

.. _release-4-0-14-fixed:

Fixed
-----

- Do not include non test environment sections or factor filters in INI configuration to factor discovery - by
  :user:`gaborbernat`. (:issue:`2746`)

.. _release-4-0-13:

*********************
 4.0.13 (2022-12-17)
*********************

.. _release-4-0-13-fixed:

Fixed
-----

- A plain section in INI configuration matching a tox environment name shadowed the laters configuration - by
  :user:`gaborbernat`. (:issue:`2636`)
- Fix space not accepted in factor filter expression - by :user:`gaborbernat`. (:issue:`2718`)

.. _release-4-0-12:

*********************
 4.0.12 (2022-12-16)
*********************

.. _release-4-0-12-fixed:

Fixed
-----

- If tox is running in a tty, allocate a pty (pseudo terminal) for commands and copy termios attributes to show colors
  and improve interactive use - by :user:`masenf`. (:issue:`1773`)
- Fix python hash seed not being set - by :user:`gaborbernat`. (:issue:`2645`)
- Fix legacy CLI flags ``--pre``, ``--force-deps``, ``--sitepackages`` and ``--alwayscopy`` not working, and mark them
  as deprecated - by :user:`gaborbernat`. (:issue:`2690`)

.. _release-4-0-12-documentation:

Documentation
-------------

- Document user level config. (:issue:`2633`)

.. _release-4-0-11:

*********************
 4.0.11 (2022-12-14)
*********************

.. _release-4-0-11-added:

Added
-----

- Modified handling of ``NO_COLOR`` environment variable, consistent with `de facto conventions
  <https://no-color.org>`_: any non-empty string will enable ``NO_COLOR`` (disable colorized output); no ``NO_COLOR``
  variable or ``NO_COLOR`` with an empty string will disable ``NO_COLOR`` (enable colorized output) - by :user:`ptmcg`.
  (:issue:`2719`)

.. _release-4-0-11-fixed:

Fixed
-----

- ``TOX_SKIP_ENV`` environment variable now works again, and can also be set via the CLI argument ``--skip-env`` for any
  command where ``-e`` can be set - by :user:`mgedmin`. (:issue:`2698`)
- ``tox config`` should only show :ref:`env_list` arguments by default instead of ``ALL`` - by :user:`gaborbernat`.
  (:issue:`2726`)

.. _release-4-0-10:

*********************
 4.0.10 (2022-12-14)
*********************

.. _release-4-0-10-added:

Added
-----

- Add ``py_dot_ver`` and ``py_impl`` constants to environments to show the current Python implementation and dot version
  (e.g. ``3.11``) for the current environment. These can be also used as substitutions in ``tox.ini`` - by
  :user:`gaborbernat`. (:issue:`2640`)

.. _release-4-0-10-fixed:

Fixed
-----

- ``--help`` now reports the default verbosity level (which is WARNING) correctly. (:issue:`2707`)

.. _release-4-0-9:

********************
 4.0.9 (2022-12-13)
********************

.. _release-4-0-9-added:

Added
-----

- Add :meth:`tox_on_install <tox.plugin.spec.tox_on_install>` and :meth:`tox_env_teardown
  <tox.plugin.spec.tox_env_teardown>` plugin hooks - by :user:`gaborbernat`. (:issue:`2687`)
- Add ``PKG_CONFIG_PATH`` to the default pass through environment list for python tox environments - by
  :user:`gaborbernat`. (:issue:`2700`)

.. _release-4-0-8:

********************
 4.0.8 (2022-12-11)
********************

.. _release-4-0-8-fixed:

Fixed
-----

- Fix multiple substitution on factor filtering in ``tox.ini`` when multiple factor filters match - by
  :user:`gaborbernat`. (:issue:`2650`)
- Fix regression in ``requirements.txt`` parsing - by :user:`gaborbernat`. (:issue:`2682`)

.. _release-4-0-7:

********************
 4.0.7 (2022-12-11)
********************

.. _release-4-0-7-fixed:

Fixed
-----

- Support for ``--no-deps`` flag within the :ref:`deps` - by :user:`gaborbernat`. (:issue:`2674`)

.. _release-4-0-6:

********************
 4.0.6 (2022-12-10)
********************

.. _release-4-0-6-added:

Added
-----

- Fail on :ref:`pass_env`/:ref:`passenv` entries containing whitespace - by :user:`ericzolf`. (:issue:`2658`)

.. _release-4-0-5:

********************
 4.0.5 (2022-12-09)
********************

.. _release-4-0-5-fixed:

Fixed
-----

- Normalize extra names passed in (fixes extra groups not being picked up during installation) - by :user:`gaborbernat`.
  (:issue:`2655`)

.. _release-4-0-4:

********************
 4.0.4 (2022-12-09)
********************

.. _release-4-0-4-fixed:

Fixed
-----

- Disable logging from ``distlib.util`` and ``filelock`` as these log messages are too verbose - by :user:`gaborbernat`.
  (:issue:`2655`)
- Use ``!r`` and ``repr()`` to better display erroneous values in exception from ``StrConverter.to_bool()`` - by
  :user:`ptmcg`. (:issue:`2665`)

.. _release-4-0-4-documentation:

Documentation
-------------

- Document that running ``--showconfig`` or ``--help-ini`` with the ``-v`` flag will add interleaved debugging
  information, whereas tox v3 added extra lines at the start - by :user:`jugmac00`. (:issue:`2622`)
- Document that tox v4 errors when using ``-U`` when defining dependencies via ``deps`` - by :user:`jugmac00`.
  (:issue:`2631`)

.. _release-4-0-3:

********************
 4.0.3 (2022-12-08)
********************

.. _release-4-0-3-fixed:

Fixed
-----

- Always set environment variable ``PYTHONIOENCODING`` to ``utf-8`` to ensure tox works under Windows custom encodings -
  by :user:`gaborbernat`. (:issue:`2422`)
- Ensure :ref:`change_dir` is created if does not exist before executing :ref:`commands` - by :user:`gaborbernat`.
  (:issue:`2620`)
- Pass through ``NUMBER_OF_PROCESSORS`` on Windows as is needed for ``multiprocessing.cpu_count`` - by
  :user:`gaborbernat`. (:issue:`2629`)
- The core tox configuration now contains ``host_python`` key showing the host python executable path - by
  :user:`gaborbernat`. (:issue:`2630`)

.. _release-4-0-3-documentation:

Documentation
-------------

- Document that space separator is no longer valid for the :ref:`passenv` and instead one should use comma - by
  :user:`gaborbernat`. (:issue:`2615`)
- Document necessity to escape ``#`` within INI configuration - by :user:`jugmac00`. (:issue:`2617`)

.. _release-4-0-2:

********************
 4.0.2 (2022-12-07)
********************

.. _release-4-0-2-fixed:

Fixed
-----

- Unescaped comma in substitution should not be replaced during INI expansion - by :user:`gaborbernat`. (:issue:`2616`)
- ``tox --showconfig -e py311`` reports tox section, though it should not - by :user:`gaborbernat`. (:issue:`2624`)

.. _release-4-0-1:

********************
 4.0.1 (2022-12-07)
********************

.. _release-4-0-1-fixed:

Fixed
-----

- Create session views of the build wheel/sdist into the :ref:`temp_dir` folder - by :user:`gaborbernat`.
  (:issue:`2612`)
- Default tox min_version to 4.0 instead of current tox version - by :user:`gaborbernat`. (:issue:`2613`)

.. _release-4-0-0:

********************
 4.0.0 (2022-12-07)
********************

.. _release-4-0-0-fixed:

Fixed
-----

- The temporary folder within the tox environment was named ``.temp`` instead of ``.tmp`` - by :user:`gaborbernat`.
  (:issue:`2608`)

.. _release-4-0-0-documentation:

Documentation
-------------

- Enumerate breaking changes of tox 4 in the FAQ, and also list major new improvements - by :user:`gaborbernat`.
  (:issue:`2587`)
- Document in the FAQ that tox 4 will raise a warning when finding conflicting environment names - by
  :user:`gaborbernat`. (:issue:`2602`)

.. _release-4-0-0rc4:

***********************
 4.0.0rc4 (2022-12-06)
***********************

.. _release-4-0-0rc4-fixed:

Fixed
-----

- Fix extras not being kept for install dependencies - by :user:`gaborbernat`. (:issue:`2603`)

.. _release-4-0-0rc4-deprecated:

Deprecated
----------

- Remove deprecated configuration option ``whitelist_externals`` which was replaced by ``allowlist_externals`` - by
  :user:`jugmac00`. (:issue:`2599`)

.. _release-4-0-0rc3:

***********************
 4.0.0rc3 (2022-12-05)
***********************

.. _release-4-0-0rc3-added:

Added
-----

- Add ``--exit-and-dump-after`` flag that allows automatically killing tox if does not finish within the passed seconds,
  and dump the thread stacks (useful to debug tox when it seemingly hangs) - by :user:`gaborbernat`. (:issue:`2595`)

.. _release-4-0-0rc3-fixed:

Fixed
-----

- Ensure that two parallel tox instance invocations on different tox environment targets will work by holding a file
  lock onto the packaging operations (e.g., in bash ``tox4 r -e py311 &; tox4 r -e py310``) - by :user:`gaborbernat`.
  (:issue:`2594`)
- Fix leaking backend processes when the build backend does not support editable wheels and fix failure when multiple
  environments exist that have a build backend that does not support editable wheels - by :user:`gaborbernat`.
  (:issue:`2595`)

.. _release-4-0-0rc2:

***********************
 4.0.0rc2 (2022-12-04)
***********************

.. _release-4-0-0rc2-added:

Added
-----

- Support for recursive extras in Python package dependencies - by :user:`gaborbernat`. (:issue:`2567`)

.. _release-4-0-0rc2-fixed:

Fixed
-----

- Support in INI files for ignore exit code marker the ``-`` without a subsequent space too - by :user:`gaborbernat`.
  (:issue:`2561`)
- Ensure paths constructed by tox are stable by resolving relative paths to fully qualified one, this insures that
  running tox from a different folder than project root still generates meaningful paths - by :user:`gaborbernat`.
  (:issue:`2562`)
- Ensure only on run environment operates at a time on a packaging environment (fixes unexpected failures when running
  in parallel mode) - by :user:`gaborbernat`. (:issue:`2564`)
- Fallback to ``editable-legacy`` if package target is ``editable`` but the build backend does not have
  ``build_editable`` hook - by :user:`gaborbernat`. (:issue:`2567`)
- Allow reference replacement in INI configuration via keys that contain the ``-`` character - by :user:`gaborbernat`.
  (:issue:`2569`)
- Resolve symlinks when saving Python executable path - by :user:`ssbarnea`. (:issue:`2574`)
- Do not set ``COLUMNS`` or ``LINES`` environment to the current TTY size if already set by the user - by
  :user:`gaborbernat`. (:issue:`2575`)
- Add missing :pypi:`build[virtualenv]<build>` test dependency - by :user:`ssbarnea`. (:issue:`2576`)

.. _release-4-0-0rc1:

***********************
 4.0.0rc1 (2022-11-29)
***********************

.. _release-4-0-0rc1-added:

Added
-----

- Add support for generative section headers - by :user:`gaborbernat`. (:issue:`2362`)

.. _release-4-0-0rc1-fixed:

Fixed
-----

- Allow installing relative paths that go outside tox root folder. - by :user:`ssbarnea`. (:issue:`2366`)

.. _release-4-0-0b3:

**********************
 4.0.0b3 (2022-11-27)
**********************

.. _release-4-0-0b3-added:

Added
-----

- Improve coloring of logged commands - by :user:`ssbarnea`. (:issue:`2356`)
- Pass ``PROGRAMDATA``, ``PROGRAMFILES(x86)``, ``PROGRAMFILES`` environments on Windows by default as it is needed for
  discovering the VS C++ compiler and start testing against 3.11 - by :user:`gaborbernat`. (:issue:`2492`)
- Support PEP-621 static metadata for getting package dependencies - by :user:`gaborbernat`. (:issue:`2499`)
- Add support for editable wheels, make it the default development mode and rename ``dev-legacy`` mode to
  ``editable-legacy`` - by :user:`gaborbernat`. (:issue:`2502`)

.. _release-4-0-0b3-fixed:

Fixed
-----

- Recognize ``TERM=dumb`` or ``NO_COLOR`` environment variables. - by :user:`ssbarnea`. (:issue:`1290`)
- Allow passing config directory without filename. - by :user:`ssbarnea`. (:issue:`2340`)
- Avoid ignored explicit argument 're' console message. - by :user:`ssbarnea`. (:issue:`2342`)
- Display registered plugins with ``tox --version`` - by :user:`mxd4`. (:issue:`2358`)
- Allow ``--hash`` to be specified in requirements.txt files. - by :user:`masenf`. (:issue:`2373`)
- Avoid impossible minversion version requirements. - by :user:`ssbarnea`. (:issue:`2414`)

.. _release-4-0-0b3-documentation:

Documentation
-------------

- Add new documentation for tox 4 - by :user:`gaborbernat`. (:issue:`2408`)

.. _release-4-0-0b2:

**********************
 4.0.0b2 (2022-04-11)
**********************

.. _release-4-0-0b2-added:

Added
-----

- Use ``tox`` console entry point name instead of ``tox4`` - by :user:`gaborbernat`. (:issue:`2344`)
- Use ``.tox`` as working directory instead of ``.tox/4`` - by :user:`gaborbernat`. (:issue:`2346`)
- Switch to ``hatchling`` as build backend instead of ``setuptools`` - by :user:`gaborbernat`. (:issue:`2368`)

.. _release-4-0-0b2-fixed:

Fixed
-----

- Fix CLI raises an error for ``-va`` with ``ignored explicit argument 'a'`` - by :user:`gaborbernat`. (:issue:`2343`)
- Do not interpolate values when parsing ``tox.ini`` configuration files - by :user:`gaborbernat`. (:issue:`2350`)

.. _release-4-0-0b2-documentation:

Documentation
-------------

- Deleted the tox mailing list -- by :user:`jugmac00` (:issue:`2364`)

.. _release-4-0-0b1:

**********************
 4.0.0b1 (2022-02-05)
**********************

.. _release-4-0-0b1-added:

Added
-----

- Display a hint for unrecognized argument CLI parse failures to use ``--`` separator to pass arguments to commands - by
  :user:`gaborbernat`. (:issue:`2183`)
- Do not allow extending the config set beyond setup to ensures that all configuration values are visible via the config
  sub-command. - by :user:`gaborbernat`. (:issue:`2243`)
- Print a message when ignoring outcome of commands - by :user:`gaborbernat`. (:issue:`2315`)

.. _release-4-0-0b1-fixed:

Fixed
-----

- Fix type annotation is broken for :meth:`tox.config.sets.ConfigSet.add_config` when adding a container type - by
  :user:`gaborbernat`. (:issue:`2233`)
- Insert ``TOX_WORK_DIR``, ``TOX_ENV_NAME``, ``TOX_ENV_DIR`` and ``VIRTUAL_ENV`` into the environment variables for all
  tox environments to keep contract with tox version 3 - by :user:`gaborbernat`. (:issue:`2259`)
- Fix plugin initialization order - core plugins first, then 3rd party and finally inline - by :user:`gaborbernat`.
  (:issue:`2264`)
- Legacy parallel mode should accept ``-p`` flag without arguments - by :user:`gaborbernat`. (:issue:`2299`)
- Sequential run fails because the packaging environment is deleted twice for sequential runs with recreate flag on - by
  :user:`gaborbernat`. (:issue:`2300`)
- Require Python 3.10 to generate docs - by :user:`jugmac00`. (:issue:`2321`)
- Environment assignment for output breaks when using ``-rv`` (when we cannot guess upfront the verbosity level from the
  CLI arguments) - by :user:`gaborbernat`. (:issue:`2324`)
- ``devenv`` command does not respect specified path - by :user:`gaborbernat`. (:issue:`2325`)

.. _release-4-0-0b1-documentation:

Documentation
-------------

- Enable link check during documentation build - by :user:`gaborbernat`. (:issue:`806`)
- Document ownership of the ``tox.wiki`` root domain - by :user:`gaborbernat`. (:issue:`2242`)
- Document :meth:`tox.config.sets.ConfigSet.loaders` - by :user:`gaborbernat`. (:issue:`2287`)
- Fix CLI documentation is missing and broken documentation references - by :user:`gaborbernat`. (:issue:`2310`)

.. _release-4-0-0a10:

***********************
 4.0.0a10 (2022-01-04)
***********************

.. _release-4-0-0a10-added:

Added
-----

- Support for grouping environment values together by applying labels to them either at :ref:`core <labels>` and
  :ref:`environment <labels-env>` level, and allow selecting them via the :ref:`-m <tox-run--m>` flag from the CLI - by
  :user:`gaborbernat`. (:issue:`238`)
- Support for environment files within the :ref:`set_env` configuration via the ``file|`` prefix - by
  :user:`gaborbernat`. (:issue:`1938`)
- Support for ``--no-provision`` flag - by :user:`gaborbernat`. (:issue:`1951`)
- Missing ``pyproject.toml`` or ``setup.py`` file at the tox root folder without the ``--install-pkg`` flag assumes no
  packaging - by :user:`gaborbernat`. (:issue:`1964`)
- Add ``external`` package type for :ref:`package` (see :ref:`external-package-builder`), and extract package
  dependencies for packages passed in via :ref:`--installpkg <tox-run---installpkg>` - by :user:`gaborbernat`.
  (:issue:`2204`)
- Add support for rewriting script invocations that have valid shebang lines when the ``TOX_LIMITED_SHEBANG``
  environment variable is set and not empty - by :user:`gaborbernat`. (:issue:`2208`)
- Support for the ``--discover`` CLI flag - by :user:`gaborbernat`. (:pr:`2245`)
- Moved the python packaging logic into a dedicate package :pypi:`pyproject-api` and use it as a dependency - by
  :user:`gaborbernat`. (:pr:`2274`)
- Drop python 3.6 support - by :user:`gaborbernat`. (:pr:`2275`)
- Support for selecting target environments with a given factor via the :ref:`-f <tox-run--f>` CLI environment flag - by
  :user:`gaborbernat`. (:pr:`2290`)

.. _release-4-0-0a10-fixed:

Fixed
-----

- Fix ``CTRL+C`` is not stopping the process on Windows - by :user:`gaborbernat`. (:issue:`2159`)
- Fix list/depends commands can create tox package environment as runtime environment and display an error message - by
  :user:`gaborbernat`. (:pr:`2234`)

.. _release-4-0-0a10-deprecated:

Deprecated
----------

- ``tox_add_core_config`` and ``tox_add_env_config`` now take a ``state: State`` argument instead of a configuration
  one, and ``Config`` not longer provides the ``envs`` property (instead users should migrate to ``State.envs``) - by
  :user:`gaborbernat`. (:pr:`2275`)

.. _release-4-0-0a9:

**********************
 4.0.0a9 (2021-09-16)
**********************

.. _release-4-0-0a9-added:

Added
-----

- Expose the parsed CLI arguments on the main configuration object for plugins and allow plugins to define their own
  configuration section -- by :user:`gaborbernat`. (:pr:`2191`)
- Let tox run fail when all envs are skipped -- by :user:`jugmac00`. (:issue:`2195`)
- Expose the configuration loading mechanism to plugins to define and load their own sections. Add
  :meth:`tox_add_env_config <tox.plugin.spec.tox_add_env_config>` plugin hook called after the configuration environment
  is created for a tox environment and removed ``tox_configure``. Add the main configuration object as argument to
  :meth:`tox_add_core_config <tox.plugin.spec.tox_add_core_config>`. Move the environment list method from the state to
  the main configuration object to allow its use within plugins -- by :user:`gaborbernat`. (:issue:`2200`)
- Allow running code in plugins before and after commands via :meth:`tox_before_run_commands
  <tox.plugin.spec.tox_before_run_commands>` and :meth:`tox_after_run_commands <tox.plugin.spec.tox_after_run_commands>`
  plugin points -- by :user:`gaborbernat`. (:issue:`2201`)
- Allow plugins to update the :ref:`set_env` and change the :ref:`pass_env` configurations -- by :user:`gaborbernat`.
  (:issue:`2215`)

.. _release-4-0-0a9-fixed:

Fixed
-----

- Fix env variable substitutions with defaults containing colon (e.g. URL) -- by :user:`comabrewer`. (:issue:`2182`)
- Do not allow constructing ``ConfigSet`` directly and implement ``__contains__`` for ``Loader`` -- by
  :user:`gaborbernat`. (:pr:`2209`)
- Fix old-new value on recreate cache miss-match are swapped -- by :user:`gaborbernat`. (:issue:`2211`)
- Report fails when report does not support Unicode characters -- by :user:`gaborbernat`. (:issue:`2213`)

.. _release-4-0-0a9-documentation:

Documentation
-------------

- Adopt furo theme, update our state diagram and description in user docs (SVG + light/dark variant), split the Python
  API into its own page from under the plugin page, and document plugin adoption under the ``tox-dev`` organization - by
  :user:`gaborbernat`. (:issue:`1881`)

.. _release-4-0-0a8:

**********************
 4.0.0a8 (2021-08-21)
**********************

.. _release-4-0-0a8-added:

Added
-----

- Add support for :ref:`allowlist_externals`, commands not matching error - by :user:`gaborbernat`. (:issue:`1127`)
- Add outcome of environments into the result json (:ref:`--result-json <tox-run---result-json>`) under the ``result``
  key containing ``success`` boolean, ``exit_code`` integer and ``duration`` float value - by :user:`gaborbernat`.
  (:issue:`1405`)
- Add ``exec`` subcommand that allows users to run an arbitrary command within the tox environment (without needing to
  modify their configuration) - by :user:`gaborbernat`. (:issue:`1790`)
- Add check to validate the base Python names and the environments name do not conflict Python spec wise, when they do
  raise error if :ref:`ignore_base_python_conflict` is not set or ``False`` - by :user:`gaborbernat`. (:issue:`1840`)
- Allow any Unix shell-style wildcards expression for :ref:`pass_env` - by :user:`gaborbernat`. (:issue:`2121`)
- Add support for :ref:`args_are_paths` flag - by :user:`gaborbernat`. (:issue:`2122`)
- Add support for :ref:`env_log_dir` (compared to tox 3 extend content and keep only last run entries) - by
  :user:`gaborbernat`. (:issue:`2123`)
- Add support for ``{:}`` substitution in ini files as placeholder for the OS path separator - by :user:`gaborbernat`.
  (:issue:`2125`)
- When cleaning directories (for tox environment, ``env_log_dir``, ``env_tmp_dir`` and packaging metadata folders) do
  not delete the directory itself and recreate, but instead just delete its content (this allows the user to cd into it
  and still be in a valid folder after a new run) - by :user:`gaborbernat`. (:pr:`2139`)
- Changes to help plugin development: simpler tox env creation argument list, expose python creation directly, allow
  skipping list dependencies install command for pip and executable is only part of the python cache for virtualenv - by
  :user:`gaborbernat`. (:pr:`2172`)

.. _release-4-0-0a8-fixed:

Fixed
-----

- Support ``#`` character in path for the tox project - by :user:`gaborbernat`. (:issue:`763`)
- If the command expression fails to parse with shlex fallback to literal pass through of the remaining elements - by
  :user:`gaborbernat`. (:issue:`1944`)
- tox config fails on :ref:`--recreate <tox-config---recreate>` flag, and once specified the output does not reflect the
  impact of the CLI flags - by :user:`gaborbernat`. (:issue:`2037`)
- Virtual environment creation for Python is always triggered at every run - by :user:`gaborbernat`. (:issue:`2041`)
- Add support for setting :ref:`suicide_timeout`, :ref:`interrupt_timeout` and :ref:`terminate_timeout` - by
  :user:`gaborbernat`. (:issue:`2124`)
- Parallel show output not working when there's a packaging phase in the run - by :user:`gaborbernat`. (:pr:`2161`)

.. _release-4-0-0a8-documentation:

Documentation
-------------

- Note constraint files are a subset of requirement files - by :user:`gaborbernat`. (:issue:`1939`)
- Add a note about having a package with different Python requirements than tox and not specifying :ref:`base_python` -
  by :user:`gaborbernat`. (:issue:`1975`)
- Fix :ref:`--runner <tox---runner>` is missing default value and documentation unclear - by :user:`gaborbernat`.
  (:issue:`2004`)

.. _release-4-0-0a7:

**********************
 4.0.0a7 (2021-07-28)
**********************

.. _release-4-0-0a7-added:

Added
-----

- Add support for configuration taken from the ``setup.cfg`` file -by :user:`gaborbernat`. (:issue:`1836`)
- Add support for configuration taken from the ``pyproject.toml`` file, ``tox`` section ``legacy_tox_ini`` key - by
  :user:`gaborbernat`. (:issue:`1837`)
- Add configuration documentation - by :user:`gaborbernat`. (:issue:`1914`)
- Implemented ``[]`` substitution (alias for ``{posargs}``) - by :user:`hexagonrecursion`. (:issue:`1928`)
- Implement ``[testenv] ignore_outcome`` - "a failing result of this testenv will not make tox fail" - by
  :user:`hexagonrecursion`. (:issue:`1947`)
- Inline plugin support via ``tox_.py``. This is loaded where the tox config source is discovered. It's a Python file
  that can contain arbitrary Python code, such as definition of a plugin. Eventually we'll add a plugin that allows
  succinct declaration/generation of new tox environments - by :user:`gaborbernat`. (:pr:`1963`)
- Introduce the installer concept, and collect pip installation into a ``pip`` package, also attach to this the
  requirements file parsing which got a major rework - by :user:`gaborbernat`. (:pr:`1991`)
- Support CPython ``3.10`` -by :user:`gaborbernat`. (:pr:`2014`)

.. _release-4-0-0a7-fixed:

Fixed
-----

- Environments with a platform mismatch are no longer silently skipped, but properly reported - by :user:`jugmac00`.
  (:issue:`1926`)
- Port pip requirements file parser to ``tox`` to achieve full equivalency (such as support for the per requirement
  ``--install-option`` and ``--global-option`` flags) - by :user:`gaborbernat`. (:issue:`1929`)
- Support for extras with paths for Python deps and requirement files - by :user:`gaborbernat`. (:issue:`1933`)
- Due to a bug ``\{posargs} {posargs}`` used to expand to literal ``{posargs} {posargs}``. Now the second ``{posargs}``
  is expanded. ``\{posargs} {posargs}`` expands to ``{posargs} positional arguments here`` - by
  :user:`hexagonrecursion`. (:issue:`1956`)
- Enable setting a different ``upstream`` repository for the coverage diff report. This has been hardcoded to
  ``upstream/rewrite`` until now. by :user:`jugmac00`. (:issue:`1972`)
- Enable replacements (a.k.a section substitutions) for section names containing a dash in sections without the
  ``testenv:`` prefix - by :user:`jugmac00`, :user:`obestwalter`, :user:`eumiro`. (:issue:`1985`)
- Fix legacy list env command for empty/missing envlist - by :user:`jugmac00`. (:issue:`1987`)
- Requirements and constraints files handling got reimplemented, which should fix all open issues related to this area -
  by :user:`gaborbernat`. (:pr:`1991`)
- Use importlib instead of ``__import__`` - by :user:`dmendek`. (:issue:`1995`)
- Evaluate factor conditions for ``command`` keys - by :user:`jugmac00`. (:issue:`2002`)
- Prefer f-strings instead of the str.format method - by :user:`eumiro`. (:issue:`2012`)
- Fix regex validation for SHA 512 hashes - by :user:`jugmac00`. (:issue:`2018`)
- Actually run all environments when ``ALL`` is provided to the legacy env command - by :user:`jugmac00`.
  (:issue:`2112`)
- Move from ``appdirs`` to ``platformdirs`` - by :user:`gaborbernat`. (:pr:`2117`)
- Move from ``toml`` to ``tomli`` - by :user:`gaborbernat`. (:pr:`2118`)

.. _release-4-0-0a7-documentation:

Documentation
-------------

- Start documenting the plugin interface. Added :meth:`tox_register_tox_env <tox.plugin.spec.tox_register_tox_env>`,
  :meth:`tox_add_option <tox.plugin.spec.tox_add_option>`, :meth:`tox_add_core_config
  <tox.plugin.spec.tox_add_core_config>`, ``tox_configure`` - by :user:`gaborbernat`. (:pr:`1991`)
- Explain how ``-v`` and ``-q`` flags play together to determine CLI verbosity level - by :user:`jugmac00`.
  (:issue:`2005`)
- Start polishing the documentation for the upcoming final release - by :user:`jugmac00`. (:pr:`2006`)
- Update documentation about changelog entries for trivial changes - by :user:`jugmac00`. (:issue:`2007`)

.. _release-4-0-0a6:

**********************
 4.0.0a6 (2021-02-15)
**********************

.. _release-4-0-0a6-added:

Added
-----

- Add basic quickstart implementation (just use pytest with the current Python version) - by :user:`gaborbernat`.
  (:issue:`1829`)
- Support comments via the ``#`` character within the ini configuration (to force a literal ``#`` use ``\#``) - by
  :user:`gaborbernat`. (:issue:`1831`)
- Add support for the ``install_command`` settings in the virtual env test environments - by :user:`gaborbernat`.
  (:issue:`1832`)
- Add support for the ``package_root`` ``setupdir`` ( Python scoped) configuration that sets the root directory used for
  packaging (the location of the historical ``setup.py`` and modern ``pyproject.toml``). This can be set at root level,
  or at tox environment level (the later takes precedence over the former) - by :user:`gaborbernat`. (:issue:`1838`)
- Implement support for the ``--installpkg`` CLI flag - by :user:`gaborbernat`. (:issue:`1839`)
- Add support for the ``list_dependencies_command`` settings in the virtual env test environments - by
  :user:`gaborbernat`. (:issue:`1842`)
- Add support for the ``ignore_errors`` settings in tox test environments - by :user:`gaborbernat`. (:issue:`1843`)
- Add support for the ``pip_pre`` settings for virtual environment based tox environments - by :user:`gaborbernat`.
  (:issue:`1844`)
- Add support for the ``platform`` settings in tox test environments - by :user:`gaborbernat`. (:issue:`1845`)
- Add support for the ``recreate`` settings in tox test environments - by :user:`gaborbernat`. (:issue:`1846`)
- Allow Python test and packaging environments with version 2.7 - by :user:`gaborbernat`. (:pr:`1900`)
- Do not construct a requirements file for deps in virtualenv, instead pass content as CLI argument to pip - by
  :user:`gaborbernat`. (:pr:`1906`)
- Do not display status update environment reports when interrupted or for the final environment ran (because at the
  final report will be soon printed and makes the status update redundant) - by :user:`gaborbernat`. (:issue:`1909`)
- The ``_TOX_SHOW_THREAD`` environment variable can be used to print alive threads when tox exists (useful to debug when
  tox hangs because of some non-finished thread) and also now prints the pid of the local subprocess when reporting the
  outcome of an execution - by :user:`gaborbernat`. (:pr:`1915`)

.. _release-4-0-0a6-fixed:

Fixed
-----

- Normalize description text to collapse newlines and one or more than whitespace to a single space - by
  :user:`gaborbernat`. (:issue:`1829`)
- Support aliases in show config key specification (will print with the primary key) - by :user:`gaborbernat`.
  (:issue:`1831`)
- Show config no longer marks as unused keys that are inherited (e.g. if the key is coming from ``testenv`` section and
  our target is ``testenv:fix``) - by :user:`gaborbernat`. (:issue:`1833`)
- ``--alwayscopy`` and ``--sitepackages`` legacy only flags do not work - by :user:`gaborbernat`. (:issue:`1839`)
- Fix handling of ``commands_pre``/``commands``/``commands_post`` to be in line with tox 3 (returned incorrect exit
  codes and post was not always executed) - by :user:`gaborbernat`. (:issue:`1843`)
- Support requirement files containing ``--hash`` constraints - by :user:`gaborbernat`. (:issue:`1903`)
- Fix a bug that caused tox to never finish when pulling configuration from a tox run environment that was never
  executed - by :user:`gaborbernat`. (:pr:`1915`)

.. _release-4-0-0a6-deprecated:

Deprecated
----------

- - Drop support for ``sdistsrc`` flag because introduces a significant complexity and is barely used (5 hits on a
    github search).
  - ``--skip-missing-interpreters``, ``--notest``, ``--sdistonly``, ``--installpkg``, ``--develop`` and
    ``--skip-pkg-install`` CLI flags are no longer available for ``devenv`` (enforce the only sane value for these). By
    :user:`gaborbernat` (:issue:`1839`)
- Remove Jenkins override support: this feature goes against the spirit of tox - blurring the line between the CI and
  local runs. It also singles out a single CI provider, which opens the door for other CIs wanting similar
  functionality. Finally, only 54 code file examples came back on a Github search, showing this is a not widely used
  feature. People who still want Jenkins override support may create a tox plugin to achieve this functionality - by
  :user:`gaborbernat`. (:issue:`1841`)

.. _release-4-0-0a5:

**********************
 4.0.0a5 (2021-01-23)
**********************

.. _release-4-0-0a5-added:

Added
-----

- Support the ``system_site_packages``/``sitepackages`` flag for virtual environment based tox environments - by
  :user:`gaborbernat`. (:issue:`1847`)
- Support the ``always_copy``/``alwayscopy`` flag for virtual environment based tox environments - by
  :user:`gaborbernat`. (:issue:`1848`)
- Support the ``download`` flag for virtual environment based tox environments - by :user:`gaborbernat`. (:issue:`1849`)
- Recreate virtual environment based tox environments when the ``virtualenv`` version changes - by :user:`gaborbernat`.
  (:issue:`1865`)

.. _release-4-0-0a5-fixed:

Fixed
-----

- Not all package dependencies are installed when different tox environments in the same run use different set of extras
  by :user:`gaborbernat`. (:issue:`1868`)
- Support ``=`` separator in requirement file flags, directories as requirements and correctly set the root of the
  requirements file when using the ``--root`` CLI flag to change the root - by :user:`gaborbernat`. (:issue:`1853`)
- Cleanup local subprocess file handlers when exiting runs (fixes ``ResourceWarning: unclosed file`` errors when running
  with ``env PYTHONTRACEMALLOC=5 PYTHONDEVMODE=y`` under a Python built with ``--with-pydebug``) - by
  :user:`gaborbernat`. (:issue:`1857`)
- Various small bugfixes:

  - honor updating default environment variables set by internal tox via set env (``PIP_DISABLE_PIP_VERSION_CHECK``)
  - do not multi-wrap ``HandledError`` in the ini file loader,
  - skipped environments are logged now with their fail message at default verbosity level,
  - fix an error that made the show configuration command crash when making the string of a config value failed,
  - support empty-new lines within the set env configurations replacements, by :user:`gaborbernat`. (:pr:`1864`)

.. _release-4-0-0a5-documentation:

Documentation
-------------

- Add CLI documentation - by :user:`gaborbernat`. (:pr:`1852`)

.. _release-4-0-0a4:

**********************
 4.0.0a4 (2021-01-16)
**********************

.. _release-4-0-0a4-added:

Added
-----

- Use ``.tox/4`` instead of ``.tox4`` folder (so ignores for tox 3 works for tox 4 too), reminder we'll rename this to
  just ``.tox`` before public release, however to encourage testing tox 4 in parallel with tox 3 this is helpful - by
  :user:`gaborbernat`. (:discussion:`1812`)
- Colorize the ``config`` command: section headers are yellow, keys are green, values remained white, exceptions are
  light red and comments are cyan - by :user:`gaborbernat`. (:pr:`1821`)

.. _release-4-0-0a4-fixed:

Fixed
-----

- Support legacy format (``-cconstraint.txt``) of constraint files in ``deps``, and expand constraint files too when
  viewing inside the ``deps`` or calculating weather our environment is up to date or not - by :user:`gaborbernat`.
  (:issue:`1788`)
- When specifying requirements/editable/constraint paths within ``deps`` escape space, unless already escaped to support
  running specifying transitive requirements files within deps - by :user:`gaborbernat`. (:issue:`1792`)
- When using a provisioned tox environment requesting ``--recreate`` failed with ``AttributeError`` - by
  :user:`gaborbernat`. (:issue:`1793`)
- Fix ``RequirementsFile`` from tox is rendered incorrectly in ``config`` command - by :user:`gaborbernat`.
  (:issue:`1820`)
- Fix a bug in the configuration system where referring to the same named key in another env/section causes circular
  dependency error - by :user:`gaborbernat`. (:pr:`1821`)
- Raise ``ValueError`` with descriptive message when a requirements file specified does not exist - by
  :user:`gaborbernat`. (:pr:`1828`)
- Support all valid requirement file specification without delimiting space in the ``deps`` of the ``tox.ini`` - by
  :user:`gaborbernat`. (:issue:`1834`)

.. _release-4-0-0a4-documentation:

Documentation
-------------

- Add code style guide for contributors - by :user:`gaborbernat`. (:issue:`1734`)

.. _release-4-0-0a3:

**********************
 4.0.0a3 (2021-01-13)
**********************

.. _release-4-0-0a3-added:

Added
-----

- Raise exception when set env enters into a circular reference - by :user:`gaborbernat`. (:issue:`1779`)
- - Raise exception when variable substitution enters into a circle.
  - Add ``{/}`` as substitution for os specific path separator.
  - Add ``{env_bin_dir}`` constant substitution.
  - Implement support for ``--discover`` flag - by :user:`gaborbernat`. (:pr:`1784`)

.. _release-4-0-0a3-fixed:

Fixed
-----

- Entries in the ``set_env`` does not reference environments from ``set_env`` - by :user:`gaborbernat`. (:issue:`1776`)
- ``env`` substitution does not uses values from ``set_env`` - by :user:`gaborbernat`. (:issue:`1779`)
- Adopt tox 3 base pass env list, by adding:

  - on all platforms: ``LANG``, ``LANGUAGE``, ``CURL_CA_BUNDLE``, ``SSL_CERT_FILE`` , ``LD_LIBRARY_PATH`` and
    ``REQUESTS_CA_BUNLDE``,
  - on Windows: ``SYSTEMDRIVE`` - by :user:`gaborbernat`. (:issue:`1780`)

- Fixed a bug that crashed tox where calling tox with the recreate flag and when multiple environments were reusing the
  same package - by :user:`gaborbernat`. (:issue:`1782`)
- - Python version markers are stripped in package dependencies (after wrongfully being detected as an extra marker).
  - In packaging APIs do not set ``PYTHONPATH`` (to empty string) if ``backend-path`` is empty.
  - Fix commands parsing on Windows (do not auto-escape ``\`` - instead users should use the new ``{\}``, and on parsed
    arguments strip both ``'`` and ``"`` quoted outcomes).
  - Allow windows paths in substitution set/default (the ``:`` character used to separate substitution arguments may
    also be present in paths on Windows - do not support single capital letter values as substitution arguments) - by
    :user:`gaborbernat`. (:pr:`1784`)
- Rework how we handle Python packaging environments:

  - the base packaging environment changed from ``.package`` to ``.pkg``,
  - merged the ``sdist``, ``wheel`` and ``dev`` separate packaging implementations into one, and internally dynamically
    pick the one that's needed,
  - the base packaging environment always uses the same Python environment as tox is installed into,
  - the base packaging environment is used to get the metadata of the project (via PEP-517) and to build ``sdist`` and
    ``dev`` packages,
  - for building wheels introduced a new per env configurable option ``wheel_build_env``, if the target Python
    major/minor and implementation for the run tox environment and the base package tox environment matches set this to
    ``.pkg``, otherwise this is ``.pkg-{implementation}{major}{minor}``,
  - internally now packaging environments can create further packaging environments they are responsible of managing,
  - updated ``depends`` to use the packaging logic,
  - add support skip missing interpreters for depends and show config, by :user:`gaborbernat`. (:issue:`1804`)

.. _release-4-0-0a2:

**********************
 4.0.0a2 (2021-01-09)
**********************

.. _release-4-0-0a2-added:

Added
-----

- Add option to disable colored output, and support ``NO_COLOR`` and ``FORCE_COLOR`` environment variables - by
  :user:`gaborbernat`. (:pr:`1630`)

.. _release-4-0-0a2-fixed:

Fixed
-----

- Fix coverage generation in CI - by :user:`gaborbernat`. (:pr:`1551`)
- Fix the CI failures:

  - drop Python 3.5 support as it's not expected to get to a release before EOL,
  - fix test using ``\n`` instead of ``os.linesep``,
  - Windows Python 3.6 does not contain ``_overlapped.ReadFileInto`` - by :user:`gaborbernat`. (:pr:`1556`)

.. _release-4-0-0a2-documentation:

Documentation
-------------

- Add base documentation by merging virtualenv structure with tox 3 - by :user:`gaborbernat`. (:pr:`1551`)

.. _release-3-28-0:

*********************
 3.28.0 (2022-12-14)
*********************

.. _release-3-28-0-added:

Added
-----

- Support provision of tox 4 with the ``min_version`` option - by :user:`hroncok` `#2661
  <https://github.com/tox-dev/tox/issues/2661>`_

.. _release-3-27-1:

*********************
 3.27.1 (2022-11-13)
*********************

.. _release-3-27-1-fixed:

Fixed
-----

- Replaced deprecated ``license_file`` key with ``license_files`` in ``setup.cfg`` -- by :user:`mgorny`. `#2521
  <https://github.com/tox-dev/tox/issues/2521>`_
- Add env cleanup to envreport - fix PYTHONPATH leak into "envreport" -- by :user:`f3flight`. `#2528
  <https://github.com/tox-dev/tox/issues/2528>`_

.. _release-3-27-0:

*********************
 3.27.0 (2022-10-25)
*********************

.. _release-3-27-0-fixed:

Fixed
-----

- Dropped ``--build-option`` in isolated builds, an alternative fix for the ``SetuptoolsDeprecationWarning`` about using
  ``--global-option`` -- by :user:`adamchainz` `#2497 <https://github.com/tox-dev/tox/issues/2497>`_
- Remove read-only files in ``ensure_empty_dir``. `#2498 <https://github.com/tox-dev/tox/issues/2498>`_
- Multiple tox instances no longer clobber the ``.tox`` directory when ``provision_tox_env`` is used. - by
  :user:`masenf` `#2515 <https://github.com/tox-dev/tox/issues/2515>`_

.. _release-3-27-0-documentation:

Documentation
-------------

- Clarify that ``install_command`` only takes one command - by :user:`jugmac00` `#2433
  <https://github.com/tox-dev/tox/issues/2433>`_
- Documented problems with plugin and provision env - by :user:`ziima`. `#2469
  <https://github.com/tox-dev/tox/issues/2469>`_

.. _release-3-26-0:

*********************
 3.26.0 (2022-09-07)
*********************

.. _release-3-26-0-added:

Added
-----

- Use ``tomllib`` on Python 3.11 or later and ``tomli`` instead of ``toml`` library on lower versions - by
  :user:`hroncok`. `#2463 <https://github.com/tox-dev/tox/issues/2463>`_

.. _release-3-26-0-fixed:

Fixed
-----

- Fix fallback to ``python`` environment when ``isolated_build = true`` is set -- by :user:`Unrud` `#2474
  <https://github.com/tox-dev/tox/issues/2474>`_
- Fixed ``SetuptoolsDeprecationWarning`` about using ``--global-option`` -- by :user:`adamchainz` `#2478
  <https://github.com/tox-dev/tox/issues/2478>`_

.. _release-3-25-1:

*********************
 3.25.1 (2022-06-29)
*********************

.. _release-3-25-1-fixed:

Fixed
-----

- ``sitepackages = true`` will add user's site-package to the python path on Windows as expected -- by :user:`niander`
  `#2402 <https://github.com/tox-dev/tox/issues/2402>`_
- Avoid importing ``pipes`` on Python 3.3+ to avoid ``DeprecationWarning`` on Python 3.11 -- by :user:`adamchainz`
  `#2417 <https://github.com/tox-dev/tox/issues/2417>`_
- Fix ``isolated_build`` when the build process produces stderr at exit. `#2449
  <https://github.com/tox-dev/tox/issues/2449>`_

.. _release-3-25-1-documentation:

Documentation
-------------

- Explain advantages of ``PIP_CONSTRAINT`` environment variable over ``--constraint`` argument. `#2423
  <https://github.com/tox-dev/tox/issues/2423>`_

.. _release-3-25-0:

*********************
 3.25.0 (2022-04-11)
*********************

.. _release-3-25-0-added:

Added
-----

- Ignore missing commands if they are prefixed by ``-`` -- by :user:`cdown`. `#2315
  <https://github.com/tox-dev/tox/issues/2315>`_
- Add default environment variables (such as http_proxy) regardless of their case to passenv on UNIX -- by
  :user:`poggenhans`. `#2372 <https://github.com/tox-dev/tox/issues/2372>`_
- On Windows ``PROGRAMFILES``, ``PROGRAMFILES(X86)``, and ``PROGRAMDATA`` environment variables are now passed through,
  unmasking system values necessary to locate resources such as a C compiler. `#2382
  <https://github.com/tox-dev/tox/issues/2382>`_

.. _release-3-25-0-fixed:

Fixed
-----

- Fixed failing isolated_build because setuptools warning was captured in ``build_requires``. -- by :user:`zariiii9003`
  `#2332 <https://github.com/tox-dev/tox/issues/2332>`_
- Avoid potential 30s delay caused by socket.getfqdn(). -- by :user:`ssbarnea` `#2375
  <https://github.com/tox-dev/tox/issues/2375>`_

.. _release-3-25-0-documentation:

Documentation
-------------

- Deleted the tox mailing list -- by :user:`jugmac00` `#2364 <https://github.com/tox-dev/tox/issues/2364>`_

.. _release-3-24-5:

*********************
 3.24.5 (2021-12-29)
*********************

.. _release-3-24-5-fixed:

Fixed
-----

- Fixed an issue where ``usedevelop`` would cause an invocation error if setup.py does not exist. -- by
  :user:`VincentVanlaer` `#2197 <https://github.com/tox-dev/tox/issues/2197>`_

.. _release-3-24-4:

*********************
 3.24.4 (2021-09-16)
*********************

.. _release-3-24-4-fixed:

Fixed
-----

- Fixed handling of ``-e ALL`` in parallel mode by ignoring the ``ALL`` in subprocesses -- by :user:`guahki`. `#2167
  <https://github.com/tox-dev/tox/issues/2167>`_
- Prevent tox from using a truncated interpreter when using ``TOX_LIMITED_SHEBANG`` -- by :user:`jdknight`. `#2208
  <https://github.com/tox-dev/tox/issues/2208>`_

.. _release-3-24-4-documentation:

Documentation
-------------

- Enabled the use of the favicon in the Sphinx docs first introduced in :issue:`764` but not integrated fully --
  :user:`webknjaz` `#2177 <https://github.com/tox-dev/tox/issues/2177>`_

.. _release-3-24-3:

*********************
 3.24.3 (2021-08-21)
*********************

.. _release-3-24-3-fixed:

Fixed
-----

- ``--parallel`` reports now show ASCII OK/FAIL/SKIP lines when full Unicode output is not available - by
  :user:`brettcs` `#1421 <https://github.com/tox-dev/tox/issues/1421>`_

.. _release-3-24-3-documentation:

Documentation
-------------

- Started enforcing valid references in Sphinx docs -- :user:`webknjaz` `#2168
  <https://github.com/tox-dev/tox/issues/2168>`_

.. _release-3-24-2:

*********************
 3.24.2 (2021-08-18)
*********************

.. _release-3-24-2-fixed:

Fixed
-----

- include ``LC_ALL`` to implicit list of passenv variables - by :user:`ssbarnea` `#2162
  <https://github.com/tox-dev/tox/issues/2162>`_

.. _release-3-24-1:

*********************
 3.24.1 (2021-07-31)
*********************

.. _release-3-24-1-fixed:

Fixed
-----

- ``get_requires_for_build_sdist`` hook (PEP 517) is assumed to return an empty list if left unimplemented by the
  backend build system - by :user:`oczkoisse` `#2130 <https://github.com/tox-dev/tox/issues/2130>`_

.. _release-3-24-1-documentation:

Documentation
-------------

- The documentation of ``install_command`` now also mentions that you can provide arbitrary commands - by
  :user:`jugmac00` `#2081 <https://github.com/tox-dev/tox/issues/2081>`_

.. _release-3-24-0:

*********************
 3.24.0 (2021-07-14)
*********************

.. _release-3-24-0-fixed:

Fixed
-----

- ``--devenv`` no longer modifies the directory in which the ``.tox`` environment is provisioned - by :user:`isaac-ped`
  `#2065 <https://github.com/tox-dev/tox/issues/2065>`_
- Fix show config when the package names are not in canonical form - by :user:`gaborbernat`. `#2103
  <https://github.com/tox-dev/tox/issues/2103>`_

.. _release-3-24-0-documentation:

Documentation
-------------

- Extended environment variables section - by :user:`majiang` `#2036 <https://github.com/tox-dev/tox/issues/2036>`_

.. _release-3-24-0-deprecated:

Deprecated
----------

- ``tox`` no longer shows deprecation warnings for ``distutils.sysconfig`` on Python 3.10 - by :user:`9999years` `#2100
  <https://github.com/tox-dev/tox/issues/2100>`_

.. _release-3-23-1:

*********************
 3.23.1 (2021-05-05)
*********************

.. _release-3-23-1-fixed:

Fixed
-----

- Distinguish between normal Windows Python and MSYS2 Python when looking for virtualenv executable path. Adds os.sep to
  ``tox.interpreters.InterpreterInfo`` - by :user:`jschwartzentruber` `#1982
  <https://github.com/tox-dev/tox/issues/1982>`_
- Fix a ``tox-conda`` isolation build bug - by :user:`AntoineD`. `#2056 <https://github.com/tox-dev/tox/issues/2056>`_

.. _release-3-23-1-documentation:

Documentation
-------------

- Update examples in the documentation to use ``setenv`` in the ``[testenv]`` sections, not wrongly in the ``[tox]``
  main section. - by :user:`AndreyNautilus` `#1999 <https://github.com/tox-dev/tox/issues/1999>`_

.. _release-3-23-1-packaging:

Packaging
---------

- Enable building tox with ``setuptools_scm`` 6+ by :user:`hroncok` `#1984
  <https://github.com/tox-dev/tox/issues/1984>`_

.. _release-3-23-0:

*********************
 3.23.0 (2021-03-03)
*********************

.. _release-3-23-0-added:

Added
-----

- tox can now be invoked with a new ``--no-provision`` flag that prevents provision, if ``requires`` or ``minversion``
  are not satisfied, tox will fail; if a path is specified as an argument to the flag (e.g. as ``tox --no-provision
  missing.json``) and provision is prevented, provision metadata are written as JSON to that path - by :user:`hroncok`
  `#1921 <https://github.com/tox-dev/tox/issues/1921>`_
- Unicode support in ``pyproject.toml`` - by :user:`domdfcoding` `#1940 <https://github.com/tox-dev/tox/issues/1940>`_

.. _release-3-22-0:

*********************
 3.22.0 (2021-02-16)
*********************

.. _release-3-22-0-added:

Added
-----

- The value of the ``requires`` configuration option is now exposed via the ``tox.config.Config`` object - by
  :user:`hroncok` `#1918 <https://github.com/tox-dev/tox/issues/1918>`_

.. _release-3-21-4:

*********************
 3.21.4 (2021-02-02)
*********************

.. _release-3-21-4-fixed:

Fixed
-----

- Adapt tests not to assume the ``easy_install`` command exists, as it was removed from ``setuptools`` 52.0.0+ - by
  :user:`hroncok` `#1893 <https://github.com/tox-dev/tox/issues/1893>`_

.. _release-3-21-3:

*********************
 3.21.3 (2021-01-28)
*********************

.. _release-3-21-3-fixed:

Fixed
-----

- Fix a killed tox (via SIGTERM) leaving the commands subprocesses running by handling it as if it were a
  KeyboardInterrupt - by :user:`dajose` `#1772 <https://github.com/tox-dev/tox/issues/1772>`_

.. _release-3-21-2:

*********************
 3.21.2 (2021-01-19)
*********************

.. _release-3-21-2-fixed:

Fixed
-----

- Newer coverage tools update the ``COV_CORE_CONTEXT`` environment variable, add it to the list of environment variables
  that can change in our pytest plugin - by :user:`gaborbernat`. `#1854 <https://github.com/tox-dev/tox/issues/1854>`_

.. _release-3-21-1:

*********************
 3.21.1 (2021-01-13)
*********************

.. _release-3-21-1-added:

Added
-----

- Prevent .tox in envlist - by :user:`jayvdb` `#1684 <https://github.com/tox-dev/tox/issues/1684>`_

.. _release-3-21-1-fixed:

Fixed
-----

- Fix regression that broke using install_command in config replacements - by :user:`jayvdb` `#1777
  <https://github.com/tox-dev/tox/issues/1777>`_
- Fix regression parsing posargs default containing colon. - by :user:`jayvdb` `#1785
  <https://github.com/tox-dev/tox/issues/1785>`_

.. _release-3-21-1-packaging:

Packaging
---------

- Enable building tox with ``setuptools_scm`` 4 and 5 by :user:`hroncok` `#1799
  <https://github.com/tox-dev/tox/issues/1799>`_

.. _release-3-21-0:

*********************
 3.21.0 (2021-01-08)
*********************

.. _release-3-21-0-added:

Added
-----

- Allow \{ and \} in default of {env:key:default}. - by :user:`jayvdb` `#1502
  <https://github.com/tox-dev/tox/issues/1502>`_
- Allow {posargs} in setenv. - by :user:`jayvdb` `#1695 <https://github.com/tox-dev/tox/issues/1695>`_
- Allow {/} to refer to os.sep. - by :user:`jayvdb` `#1700 <https://github.com/tox-dev/tox/issues/1700>`_
- Make parsing [testenv] sections in setup.cfg official. - by :user:`mauvilsa` `#1727
  <https://github.com/tox-dev/tox/issues/1727>`_
- Relax importlib requirement to allow 3.0.0 or any newer version - by :user:`pkolbus` `#1763
  <https://github.com/tox-dev/tox/issues/1763>`_

.. _release-3-21-0-fixed:

Fixed
-----

- Fix the false ``congratulations`` message that appears when a ``KeyboardInterrupt`` occurs during package
  installation. - by :user:`gnikonorov` `#1453 <https://github.com/tox-dev/tox/issues/1453>`_
- Fix ``platform`` support for ``install_command``. - by :user:`jayvdb` `#1464
  <https://github.com/tox-dev/tox/issues/1464>`_
- Fixed regression in v3.20.0 that caused escaped curly braces in setenv to break usage of the variable elsewhere in
  tox.ini. - by :user:`jayvdb` `#1690 <https://github.com/tox-dev/tox/issues/1690>`_
- Prevent ``{}`` and require ``{:`` is only followed by ``}``. - by :user:`jayvdb` `#1711
  <https://github.com/tox-dev/tox/issues/1711>`_
- Raise ``MissingSubstitution`` on access of broken ini setting. - by :user:`jayvdb` `#1716
  <https://github.com/tox-dev/tox/issues/1716>`_

.. _release-3-21-0-documentation:

Documentation
-------------

- Document more info about using ``platform`` setting. - by :user:`prakhargurunani` `#1144
  <https://github.com/tox-dev/tox/issues/1144>`_
- Replace ``indexserver`` in documentation with environment variables - by :user:`ziima`. `#1357
  <https://github.com/tox-dev/tox/issues/1357>`_
- Document that the ``passenv`` environment setting is case insensitive. - by :user:`gnikonorov` `#1534
  <https://github.com/tox-dev/tox/issues/1534>`_

.. _release-3-20-1:

*********************
 3.20.1 (2020-10-09)
*********************

.. _release-3-20-1-fixed:

Fixed
-----

- Relax importlib requirement to allow version<3 - by :user:`usamasadiq` `#1682
  <https://github.com/tox-dev/tox/issues/1682>`_

.. _release-3-20-0:

*********************
 3.20.0 (2020-09-01)
*********************

.. _release-3-20-0-added:

Added
-----

- Support for comments within ``setenv`` and environment files via the ``files|`` prefix. - by :user:`gaborbernat`
  `#1667 <https://github.com/tox-dev/tox/issues/1667>`_

.. _release-3-20-0-fixed:

Fixed
-----

- Allow hyphens and empty factors in generative section name. - by :user:`tyagdit` `#1636
  <https://github.com/tox-dev/tox/issues/1636>`_
- Support for PEP517 in-tree build backend-path key in ``get-build-requires``. - by :user:`nizox` `#1654
  <https://github.com/tox-dev/tox/issues/1654>`_
- Allow escaping curly braces in setenv. - by :user:`mkenigs` `#1656 <https://github.com/tox-dev/tox/issues/1656>`_

.. _release-3-19-0:

*********************
 3.19.0 (2020-08-06)
*********************

.. _release-3-19-0-added:

Added
-----

- Implement support for building projects having :PEP:`517#in-tree-build-backends` ``backend-path`` setting - by
  :user:`webknjaz` `#1575 <https://github.com/tox-dev/tox/issues/1575>`_
- Don't require a tox config file for ``tox --devenv`` - by :user:`hroncok` `#1643
  <https://github.com/tox-dev/tox/issues/1643>`_

.. _release-3-19-0-fixed:

Fixed
-----

- skip ``setup.cfg`` if it has no ``tox:tox`` namespace - by :user:`hroncok` `#1045
  <https://github.com/tox-dev/tox/issues/1045>`_

.. _release-3-19-0-documentation:

Documentation
-------------

- Fixed grammar in top-level documentation - by :user:`tfurf` `#1631 <https://github.com/tox-dev/tox/issues/1631>`_

.. _release-3-18-1:

*********************
 3.18.1 (2020-07-28)
*********************

.. _release-3-18-1-fixed:

Fixed
-----

- Fix ``TypeError`` when using isolated_build with backends that are not submodules (e.g. ``maturin``) `#1629
  <https://github.com/tox-dev/tox/issues/1629>`_

.. _release-3-18-0:

*********************
 3.18.0 (2020-07-23)
*********************

.. _release-3-18-0-deprecated:

Deprecated
----------

- Add allowlist_externals alias to whitelist_externals (whitelist_externals is now deprecated). - by :user:`dajose`
  `#1491 <https://github.com/tox-dev/tox/issues/1491>`_

.. _release-3-17-1:

*********************
 3.17.1 (2020-07-15)
*********************

.. _release-3-17-1-fixed:

Fixed
-----

- Fix tests when the ``HOSTNAME`` environment variable is set, but empty string - by :user:`hroncok` `#1616
  <https://github.com/tox-dev/tox/issues/1616>`_

.. _release-3-17-0:

*********************
 3.17.0 (2020-07-14)
*********************

.. _release-3-17-0-added:

Added
-----

- The long arguments ``--verbose`` and ``--quiet`` (rather than only their short forms, ``-v`` and ``-q``) are now
  accepted. `#1612 <https://github.com/tox-dev/tox/issues/1612>`_
- The ``ResultLog`` now prefers ``HOSTNAME`` environment variable value (if set) over the full qualified domain name of
  localhost. This makes it possible to disable an undesired DNS lookup, which happened on all ``tox`` invocations,
  including trivial ones - by :user:`hroncok` `#1615 <https://github.com/tox-dev/tox/issues/1615>`_

.. _release-3-17-0-documentation:

Documentation
-------------

- Update packaging information for Flit. `#1613 <https://github.com/tox-dev/tox/issues/1613>`_

.. _release-3-16-1:

*********************
 3.16.1 (2020-06-29)
*********************

.. _release-3-16-1-fixed:

Fixed
-----

- Fixed the support for using ``{temp_dir}`` in ``tox.ini`` - by :user:`webknjaz` `#1609
  <https://github.com/tox-dev/tox/issues/1609>`_

.. _release-3-16-0:

*********************
 3.16.0 (2020-06-26)
*********************

.. _release-3-16-0-added:

Added
-----

- Allow skipping the package and installation step when passing the ``--skip-pkg-install``. This should be used in pair
  with the ``--notest``, so you can separate environment setup and test run: .. code-block:: console tox -e py --notest
  tox -e py --skip-pkg-install by :user:`gaborbernat`. `#1605 <https://github.com/tox-dev/tox/issues/1605>`_

.. _release-3-16-0-performance:

Performance
-----------

- Improve config parsing performance by precompiling commonly used regular expressions - by :user:`brettlangdon` `#1603
  <https://github.com/tox-dev/tox/issues/1603>`_

.. _release-3-15-2:

*********************
 3.15.2 (2020-06-06)
*********************

.. _release-3-15-2-added:

Added
-----

- Allow to run the tests with pip 19.3.1 once again while preserving the ability to use pip 20.1 - by :user:`hroncok`
  `#1594 <https://github.com/tox-dev/tox/issues/1594>`_

.. _release-3-15-2-fixed:

Fixed
-----

- Add an option to allow a process to suicide before sending the SIGTERM. - by :user:`jhesketh` `#1497
  <https://github.com/tox-dev/tox/issues/1497>`_
- PyPy 7.3.1 on Windows uses the ``Script`` folder instead of ``bin``. - by :user:`gaborbernat` `#1597
  <https://github.com/tox-dev/tox/issues/1597>`_

.. _release-3-15-1:

*********************
 3.15.1 (2020-05-20)
*********************

.. _release-3-15-1-fixed:

Fixed
-----

- ``tox --showconfig`` no longer tries to interpolate '%' signs. `#1585 <https://github.com/tox-dev/tox/issues/1585>`_

.. _release-3-15-0:

*********************
 3.15.0 (2020-05-02)
*********************

.. _release-3-15-0-added:

Added
-----

- Allow parallel mode without arguments. - by :user:`ssbarnea` `#1418 <https://github.com/tox-dev/tox/issues/1418>`_
- Allow generative section name expansion. - by :user:`bruchar1` `#1545 <https://github.com/tox-dev/tox/issues/1545>`_
- default to passing the env var PIP_EXTRA_INDEX_URL by :user:`georgealton`. `#1561
  <https://github.com/tox-dev/tox/issues/1561>`_

.. _release-3-15-0-fixed:

Fixed
-----

- Respect attempts to change ``PATH`` via ``setenv`` - by :user:`aklajnert`. `#1423
  <https://github.com/tox-dev/tox/issues/1423>`_
- Fix parsing of architecture in python interpreter name. - by :user:`bruchar1` `#1542
  <https://github.com/tox-dev/tox/issues/1542>`_
- Prevent exception when command is empty. - by :user:`bruchar1` `#1544 <https://github.com/tox-dev/tox/issues/1544>`_
- Fix irrelevant Error message for invalid argument when running outside a directory with tox support files by
  :user:`nkpro2000sr`. `#1547 <https://github.com/tox-dev/tox/issues/1547>`_

.. _release-3-15-0-documentation:

Documentation
-------------

- Improve documentation about config by adding tox environment description at start - by :user:`stephenfin`. `#1573
  <https://github.com/tox-dev/tox/issues/1573>`_

.. _release-3-14-6:

*********************
 3.14.6 (2020-03-25)
*********************

.. _release-3-14-6-fixed:

Fixed
-----

- Exclude virtualenv dependency versions with known regressions (20.0.[0-7]) - by :user:`webknjaz`. `#1537
  <https://github.com/tox-dev/tox/issues/1537>`_
- Fix ``tox -h`` and ``tox --hi`` shows an error when run outside a directory with tox support files by
  :user:`nkpro2000sr`. `#1539 <https://github.com/tox-dev/tox/issues/1539>`_
- Fix ValueError on ``tox -l`` for a ``tox.ini`` file that does not contain an ``envlist`` definition. - by
  :user:`jquast`. `#1343 <https://github.com/tox-dev/tox/issues/1343>`_

.. _release-3-14-5:

*********************
 3.14.5 (2020-02-16)
*********************

.. _release-3-14-5-added:

Added
-----

- Add ``--discover`` (fallback to ``TOX_DISCOVER`` environment variable via path separator) to inject python executables
  to try as first step of a discovery - note the executable still needs to match the environment by :user:`gaborbernat`.
  `#1526 <https://github.com/tox-dev/tox/issues/1526>`_

.. _release-3-14-4:

*********************
 3.14.4 (2020-02-13)
*********************

.. _release-3-14-4-added:

Added
-----

- Add ``interrupt_timeout`` and ``terminate_timeout`` that configure delay between SIGINT, SIGTERM and SIGKILL when tox
  is interrupted. - by :user:`sileht` `#1493 <https://github.com/tox-dev/tox/issues/1493>`_
- Add ``HTTP_PROXY``, ``HTTPS_PROXY`` and ``NO_PROXY`` to default passenv. - by :user:`pfmoore` `#1498
  <https://github.com/tox-dev/tox/issues/1498>`_

.. _release-3-14-4-fixed:

Fixed
-----

- Bump minimal six version needed to avoid using one incompatible with newer virtualenv. - by :user:`ssbarnea` `#1519
  <https://github.com/tox-dev/tox/issues/1519>`_
- Avoid pypy test failure due to undefined printout var. - by :user:`ssbarnea` `#1521
  <https://github.com/tox-dev/tox/issues/1521>`_

.. _release-3-14-3:

*********************
 3.14.3 (2019-12-27)
*********************

.. _release-3-14-3-fixed:

Fixed
-----

- Relax importlib requirement to allow either version 0 or 1 - by :user:`chyzzqo2` `#1476
  <https://github.com/tox-dev/tox/issues/1476>`_

.. _release-3-14-3-packaging:

Packaging
---------

- Clarify legacy setup.py error message: python projects should commit to a strong consistency of message regarding
  packaging. We no-longer tell people to add a setup.py to their already configured pep-517 project, otherwise it could
  imply that pyproject.toml isn't as well supported and recommended as it truly is - by :user:`graingert` `#1478
  <https://github.com/tox-dev/tox/issues/1478>`_

.. _release-3-14-2:

*********************
 3.14.2 (2019-12-02)
*********************

.. _release-3-14-2-fixed:

Fixed
-----

- Fix fallback to global configuration when running in Jenkins. - by :user:`daneah` `#1428
  <https://github.com/tox-dev/tox/issues/1428>`_
- Fix coloring on windows: colorama is a dep. - by :user:`1138-4EB` `#1471
  <https://github.com/tox-dev/tox/issues/1471>`_

.. _release-3-14-2-performance:

Performance
-----------

- improve performance with internal lookup of Python version information - by :user:`blueyed` `#1462
  <https://github.com/tox-dev/tox/issues/1462>`_

.. _release-3-14-2-packaging:

Packaging
---------

- Use latest version of importlib_metadata package - by :user:`kammala` `#1472
  <https://github.com/tox-dev/tox/issues/1472>`_
- Mark poetry related tests as xfail since its dependency pyrsistent won't install in ci due to missing wheels/build
  deps. - by :user:`RonnyPfannschmidt` `#1474 <https://github.com/tox-dev/tox/issues/1474>`_

.. _release-3-14-1:

*********************
 3.14.1 (2019-11-13)
*********************

.. _release-3-14-1-fixed:

Fixed
-----

- fix reporting of exiting due to (real) signals - by :user:`blueyed` `#1401
  <https://github.com/tox-dev/tox/issues/1401>`_
- Bump minimal virtualenv to 16.0.0 to improve own transitive deps handling in some ancient envs. — by :user:`webknjaz`
  `#1429 <https://github.com/tox-dev/tox/issues/1429>`_
- Adds ``CURL_CA_BUNDLE``, ``REQUESTS_CA_BUNDLE``, ``SSL_CERT_FILE`` to the default passenv values. - by
  :user:`ssbarnea` `#1437 <https://github.com/tox-dev/tox/issues/1437>`_
- Fix nested tox execution in the parallel mode by separating the environment variable that let's tox know it is invoked
  in the parallel mode (``_TOX_PARALLEL_ENV``) from the variable that informs the tests that tox is running in parallel
  mode (``TOX_PARALLEL_ENV``). — by :user:`hroncok` `#1444 <https://github.com/tox-dev/tox/issues/1444>`_
- Fix provisioning from a pyvenv interpreter. — by :user:`kentzo` `#1452 <https://github.com/tox-dev/tox/issues/1452>`_
  Deprecations (removal in next major release)
- Python ``3.4`` is no longer supported. — by :user:`gaborbernat` `#1456 <https://github.com/tox-dev/tox/issues/1456>`_

.. _release-3-14-0:

*********************
 3.14.0 (2019-09-03)
*********************

.. _release-3-14-0-added:

Added
-----

- Add support for minor versions with multiple digits ``tox -e py310`` works for ``python3.10`` - by :user:`asottile`
  `#1374 <https://github.com/tox-dev/tox/issues/1374>`_
- Remove dependence on ``md5`` hashing algorithm - by :user:`asottile` `#1384
  <https://github.com/tox-dev/tox/issues/1384>`_

.. _release-3-14-0-changes:

Changes
-------

- ￼Fix relative URLs to files in the repo in ``.github/PULL_REQUEST_TEMPLATE.md`` — by :user:`webknjaz` `#1363
  <https://github.com/tox-dev/tox/issues/1363>`_
- Replace ``importlib_metadata`` backport with ``importlib.metadata`` from the standard library on Python ``3.8+`` - by
  :user:`hroncok` `#1367 <https://github.com/tox-dev/tox/issues/1367>`_
- Render the change fragment help on the ``docs/changelog/`` directory view on GitHub — by :user:`webknjaz` `#1370
  <https://github.com/tox-dev/tox/issues/1370>`_

.. _release-3-14-0-fixed:

Fixed
-----

- Fix ``PythonSpec`` detection of ``python3.10`` - by :user:`asottile` `#1374
  <https://github.com/tox-dev/tox/issues/1374>`_
- Fix regression failing to detect future and past ``py##`` factors - by :user:`asottile` `#1377
  <https://github.com/tox-dev/tox/issues/1377>`_
- Fix ``current_tox_py`` for ``pypy`` / ``pypy3`` - by :user:`asottile` `#1378
  <https://github.com/tox-dev/tox/issues/1378>`_
- Honor environment markers in ``requires`` list - by :user:`asottile` `#1380
  <https://github.com/tox-dev/tox/issues/1380>`_
- improve recreate check by allowing directories containing ``.tox-config1`` (the marker file created by tox) - by
  :user:`asottile` `#1383 <https://github.com/tox-dev/tox/issues/1383>`_
- Recognize correctly interpreters that have suffixes (like python3.7-dbg). `#1415
  <https://github.com/tox-dev/tox/issues/1415>`_

.. _release-3-14-0-documentation:

Documentation
-------------

- clarify behavior if recreate is set to false - by :user:`PJCampi` `#1399
  <https://github.com/tox-dev/tox/issues/1399>`_

.. _release-3-13-2:

*********************
 3.13.2 (2019-07-01)
*********************

.. _release-3-13-2-fixed:

Fixed
-----

- on venv cleanup: add explicit check for pypy venv to make it possible to recreate it - by :user:`obestwalter` `#1355
  <https://github.com/tox-dev/tox/issues/1355>`_
- non canonical names within ``requires`` cause infinite provisioning loop - by :user:`gaborbernat` `#1359
  <https://github.com/tox-dev/tox/issues/1359>`_

.. _release-3-13-1:

*********************
 3.13.1 (2019-06-25)
*********************

.. _release-3-13-1-fixed:

Fixed
-----

- Fix isolated build double-requirement - by :user:`asottile`. `#1349 <https://github.com/tox-dev/tox/issues/1349>`_

.. _release-3-13-0:

*********************
 3.13.0 (2019-06-24)
*********************

.. _release-3-13-0-added:

Added
-----

- Replace ``pkg_resources`` with ``importlib_metadata`` for speed - by :user:`asottile`. `#1324
  <https://github.com/tox-dev/tox/issues/1324>`_
- Add the ``--devenv ENVDIR`` option for creating development environments from ``[testenv]`` configurations - by
  :user:`asottile`. `#1326 <https://github.com/tox-dev/tox/issues/1326>`_
- Refuse to delete ``envdir`` if it doesn't look like a virtualenv - by :user:`asottile`. `#1340
  <https://github.com/tox-dev/tox/issues/1340>`_

.. _release-3-13-0-fixed:

Fixed
-----

- tox used Windows shell rules on non-Windows platforms when transforming positional arguments to a string - by
  :user:`barneygale`. `#1336 <https://github.com/tox-dev/tox/issues/1336>`_

.. _release-3-12-1:

*********************
 3.12.1 (2019-05-23)
*********************

.. _release-3-12-1-fixed:

Fixed
-----

- Ensure ``TOX_WORK_DIR`` is a native string in ``os.environ`` - by :user:`asottile`. `#1313
  <https://github.com/tox-dev/tox/issues/1313>`_
- Fix import and usage of ``winreg`` for python2.7 on windows - by :user:`asottile`. `#1315
  <https://github.com/tox-dev/tox/issues/1315>`_
- Fix Windows selects incorrect spec on first discovery - by :user:`gaborbernat` `#1317
  <https://github.com/tox-dev/tox/issues/1317>`_

.. _release-3-12-0:

*********************
 3.12.0 (2019-05-23)
*********************

.. _release-3-12-0-added:

Added
-----

- Adding ``TOX_PARALLEL_NO_SPINNER`` environment variable to disable the spinner in parallel mode for the purposes of
  clean output when using CI tools - by :user:`zeroshift` `#1184 <https://github.com/tox-dev/tox/issues/1184>`_

.. _release-3-12-0-fixed:

Fixed
-----

- When using ``--parallel`` with ``--result-json`` the test results are now included the same way as with serial runs -
  by :user:`fschulze` `#1295 <https://github.com/tox-dev/tox/issues/1295>`_
- Turns out the output of the ``py -0p`` is not stable yet and varies depending on various edge cases. Instead now we
  read the interpreter values directly from registry via `PEP-514 <https://www.python.org/dev/peps/pep-0514>`_ - by
  :user:`gaborbernat`. `#1306 <https://github.com/tox-dev/tox/issues/1306>`_

.. _release-3-11-1:

*********************
 3.11.1 (2019-05-16)
*********************

.. _release-3-11-1-fixed:

Fixed
-----

- When creating virtual environments we no longer ask the python to tell its path, but rather use the discovered path.
  `#1301 <https://github.com/tox-dev/tox/issues/1301>`_

.. _release-3-11-0:

*********************
 3.11.0 (2019-05-15)
*********************

.. _release-3-11-0-added:

Added
-----

- ``--showconfig`` overhaul:

  - now fully generated via the config parser, so anyone can load it by using the built-in python config parser
  - the ``tox`` section contains all configuration data from config
  - the ``tox`` section contains a ``host_python`` key detailing the path of the host python
  - the ``tox:version`` section contains the versions of all packages tox depends on with their version
  - passing ``-l`` now allows only listing default target envs
  - allows showing config for a given set of tox environments only via the ``-e`` cli flag or the ``TOXENV`` environment
    variable, in this case the ``tox`` and ``tox:version`` section is only shown if at least one verbosity flag is
    passed this should help inspecting the options. `#1298 <https://github.com/tox-dev/tox/issues/1298>`_

.. _release-3-10-0:

*********************
 3.10.0 (2019-05-13)
*********************

.. _release-3-10-0-added:

Added
-----

- Virtual environments created now no longer upgrade pip/wheel/setuptools to the latest version. Instead the start
  packages after virtualenv creation now is whatever virtualenv has bundled in. This allows faster virtualenv creation
  and builds that are easier to reproduce. `#448 <https://github.com/tox-dev/tox/issues/448>`_
- Improve python discovery and add architecture support:

  - UNIX: - First, check if the tox host Python matches. - Second, check if the the canonical name (e.g. ``python3.7``,
    ``python3``) matches or the base python is an absolute path, use that. - Third, check if the the canonical name
    without version matches (e.g. ``python``, ``pypy``) matches.
  - Windows: - First, check if the tox host Python matches. - Second, use the ``py.exe`` to list registered interpreters
    and any of those match. - Third, check if the the canonical name (e.g. ``python3.7``, ``python3``) matches or the
    base python is an absolute path, use that. - Fourth, check if the the canonical name without version matches (e.g.
    ``python``, ``pypy``) matches. - Finally, check for known locations (``c:\python{major}{minor}\python.exe``). tox
    environment configuration generation is now done in parallel (to alleviate the slowdown due to extra checks). `#1290
    <https://github.com/tox-dev/tox/issues/1290>`_

.. _release-3-10-0-fixed:

Fixed
-----

- fix for ``tox -l`` command: do not allow setting the ``TOXENV`` or the ``-e`` flag to override the listed default
  environment variables, they still show up under extra if non defined target - by :user:`gaborbernat` `#720
  <https://github.com/tox-dev/tox/issues/720>`_
- tox ignores unknown CLI arguments when provisioning is on and outside of the provisioned environment (allowing
  provisioning arguments to be forwarded freely) - by :user:`gaborbernat` `#1270
  <https://github.com/tox-dev/tox/issues/1270>`_

.. _release-3-9-0:

********************
 3.9.0 (2019-04-17)
********************

.. _release-3-9-0-added:

Added
-----

- Allow having inline comments in ``deps`` — by :user:`webknjaz` `#1262 <https://github.com/tox-dev/tox/issues/1262>`_

.. _release-3-9-0-fixed:

Fixed
-----

- Fix ``congratulations`` when using ``^C`` during virtualenv creation - by :user:`asottile` `#1257
  <https://github.com/tox-dev/tox/issues/1257>`_

.. _release-3-8-6:

********************
 3.8.6 (2019-04-03)
********************

.. _release-3-8-6-fixed:

Fixed
-----

- ``parallel_show_output`` does not work with tox 3.8 `#1245 <https://github.com/tox-dev/tox/issues/1245>`_

.. _release-3-8-5:

********************
 3.8.5 (2019-04-03)
********************

.. _release-3-8-5-fixed:

Fixed
-----

- the isolated build env now ignores ``sitepackages``, ``deps`` and ``description`` as these do not make sense - by
  :user:`gaborbernat` `#1239 <https://github.com/tox-dev/tox/issues/1239>`_
- Do not print timings with more than 3 decimal digits on Python 3 - by :user:`mgedmin`. `#1241
  <https://github.com/tox-dev/tox/issues/1241>`_

.. _release-3-8-4:

********************
 3.8.4 (2019-04-01)
********************

.. _release-3-8-4-fixed:

Fixed
-----

- Fix sdist creation on python2.x when there is non-ascii output. `#1234 <https://github.com/tox-dev/tox/issues/1234>`_
- fix typos in isolated.py that made it impossible to install package with requirements in pyproject.toml - by
  :user:`unmade` `#1236 <https://github.com/tox-dev/tox/issues/1236>`_

.. _release-3-8-3:

********************
 3.8.3 (2019-03-29)
********************

.. _release-3-8-3-fixed:

Fixed
-----

- don't crash when version information is not available for a proposed base python - by :user:`gaborbernat` `#1227
  <https://github.com/tox-dev/tox/issues/1227>`_
- Do not print exception traceback when the provisioned tox fails - by :user:`gaborbernat` `#1228
  <https://github.com/tox-dev/tox/issues/1228>`_

.. _release-3-8-2:

********************
 3.8.2 (2019-03-29)
********************

.. _release-3-8-2-fixed:

Fixed
-----

- using -v and -e connected (as -ve) fails - by :user:`gaborbernat` `#1218
  <https://github.com/tox-dev/tox/issues/1218>`_
- Changes to the plugin tester module (cmd no longer sets ``PYTHONPATH``), and ``action.popen`` no longer returns the
  command identifier information from within the logs. No public facing changes. `#1222
  <https://github.com/tox-dev/tox/issues/1222>`_
- Spinner fails in CI on ``UnicodeEncodeError`` - by :user:`gaborbernat` `#1223
  <https://github.com/tox-dev/tox/issues/1223>`_

.. _release-3-8-1:

********************
 3.8.1 (2019-03-28)
********************

.. _release-3-8-1-fixed:

Fixed
-----

- The ``-eALL`` command line argument now expands the ``envlist`` key and includes all its environment. `#1155
  <https://github.com/tox-dev/tox/issues/1155>`_
- Isolated build environment dependency overrides were not taken in consideration (and such it inherited the deps from
  the testenv section) - by :user:`gaborbernat` `#1207 <https://github.com/tox-dev/tox/issues/1207>`_
- ``--result-json`` puts the command into setup section instead of test (pre and post commands are now also correctly
  put into the commands section) - by :user:`gaborbernat` `#1210 <https://github.com/tox-dev/tox/issues/1210>`_
- Set ``setup.cfg`` encoding to UTF-8 as it contains Unicode characters. `#1212
  <https://github.com/tox-dev/tox/issues/1212>`_
- Fix tox CI, better error reporting when locating via the py fails - by :user:`gaborbernat` `#1215
  <https://github.com/tox-dev/tox/issues/1215>`_

.. _release-3-8-0:

********************
 3.8.0 (2019-03-27)
********************

.. _release-3-8-0-added:

Added
-----

- tox now auto-provisions itself if needed (see :ref:`auto-provisioning`). Plugins or minimum version of tox no longer
  need to be manually satisfied by the user, increasing their ease of use. - by :user:`gaborbernat` `#998
  <https://github.com/tox-dev/tox/issues/998>`_
- tox will inject the ``TOX_PARALLEL_ENV`` environment variable, set to the current running tox environment name, only
  when running in parallel mode. - by :user:`gaborbernat` `#1139 <https://github.com/tox-dev/tox/issues/1139>`_
- Parallel children now save their output to a disk logfile - by :user:`gaborbernat` `#1143
  <https://github.com/tox-dev/tox/issues/1143>`_
- Parallel children now are added to ``--result-json`` - by :user:`gaborbernat` `#1159
  <https://github.com/tox-dev/tox/issues/1159>`_
- Display pattern and ``sys.platform`` with platform mismatch - by :user:`blueyed`. `#1176
  <https://github.com/tox-dev/tox/issues/1176>`_
- Setting the environment variable ``TOX_REPORTER_TIMESTAMP`` to ``1`` will enable showing for each output line its
  delta since the tox startup. This can be especially handy when debugging parallel runs.- by :user:`gaborbernat` `#1203
  <https://github.com/tox-dev/tox/issues/1203>`_

.. _release-3-8-0-fixed:

Fixed
-----

- In a posix shell, setting the PATH environment variable to an empty value is equivalent to not setting it at all;
  therefore we no longer if the user sets PYTHONPATH an empty string on python 3.4 or later - by :user:`gaborbernat`.
  `#1092 <https://github.com/tox-dev/tox/issues/1092>`_
- Fixed bug of children process calls logs clashing (log already exists) - by :user:`gaborbernat` `#1137
  <https://github.com/tox-dev/tox/issues/1137>`_
- Interpreter discovery and virtualenv creation process calls that failed will now print out on the screen their output
  (via the logfile we automatically save) - by :user:`gaborbernat` `#1150 <https://github.com/tox-dev/tox/issues/1150>`_
- Using ``py2`` and ``py3`` with a specific ``basepython`` will no longer raise a warning unless the major version
  conflicts - by :user:`demosdemon`. `#1153 <https://github.com/tox-dev/tox/issues/1153>`_
- Fix missing error for ``tox -e unknown`` when tox.ini declares ``envlist``. - by :user:`medmunds` `#1160
  <https://github.com/tox-dev/tox/issues/1160>`_
- Resolve symlinks with ``toxworkdir`` - by :user:`blueyed`. `#1169 <https://github.com/tox-dev/tox/issues/1169>`_
- Interrupting a tox call (e.g. via CTRL+C) now will ensure that spawn child processes (test calls, interpreter
  discovery, parallel sub-instances, provisioned hosts) are correctly stopped before exiting (via the pattern of
  INTERRUPT - 300 ms, TERMINATE - 200 ms, KILL signals) - by :user:`gaborbernat` `#1172
  <https://github.com/tox-dev/tox/issues/1172>`_
- Fix a ``ResourceWarning: unclosed file`` in ``Action`` - by :user:`BoboTiG`. `#1179
  <https://github.com/tox-dev/tox/issues/1179>`_
- Fix deadlock when using ``--parallel`` and having environments with lots of output - by :user:`asottile`. `#1183
  <https://github.com/tox-dev/tox/issues/1183>`_
- Removed code that sometimes caused a difference in results between ``--parallel`` and ``-p`` when using ``posargs`` -
  by :user:`timdaman` `#1192 <https://github.com/tox-dev/tox/issues/1192>`_

.. _release-3-8-0-documentation:

Documentation
-------------

- Add a ``poetry`` examples to packaging - by :user:`gaborbernat` `#1163 <https://github.com/tox-dev/tox/issues/1163>`_

.. _release-3-7-0:

********************
 3.7.0 (2019-01-11)
********************

.. _release-3-7-0-added:

Added
-----

- Parallel mode added (alternative to ``detox`` which is being deprecated), for more details see :ref:`parallel_mode` -
  by :user:`gaborbernat`. `#439 <https://github.com/tox-dev/tox/issues/439>`_
- Added command line shortcut ``-s`` for ``--skip-missing-interpreters`` - by :user:`evandrocoan` `#1119
  <https://github.com/tox-dev/tox/issues/1119>`_ Deprecations (removal in next major release)
- Whitelisting of externals will be mandatory in tox 4: issue a deprecation warning as part of the already existing
  warning - by :user:`obestwalter` `#1129 <https://github.com/tox-dev/tox/issues/1129>`_

.. _release-3-7-0-documentation:

Documentation
-------------

- Clarify explanations in examples and avoid unsupported end line comments - by :user:`obestwalter` `#1110
  <https://github.com/tox-dev/tox/issues/1110>`_
- Set to PULL_REQUEST_TEMPLATE.md use relative instead of absolute URLs - by :user:`evandrocoan` Fixed
  PULL_REQUEST_TEMPLATE.md path for changelog/examples.rst to docs/changelog/examples.rst - by :user:`evandrocoan`
  `#1120 <https://github.com/tox-dev/tox/issues/1120>`_

.. _release-3-6-1:

********************
 3.6.1 (2018-12-24)
********************

.. _release-3-6-1-added:

Added
-----

- if the packaging phase successfully builds a package set it as environment variable under ``TOX_PACKAGE`` (useful to
  make assertions on the built package itself, instead of just how it ends up after installation) - by
  :user:`gaborbernat` (`#1081 <https://github.com/tox-dev/tox/issues/1081>`_)

.. _release-3-6-0:

********************
 3.6.0 (2018-12-13)
********************

.. _release-3-6-0-fixed:

Fixed
-----

- On windows, check ``sys.executable`` before others for interpreter version lookup. This matches what happens on
  non-windows. (`#1087 <https://github.com/tox-dev/tox/issues/1087>`_)
- Don't rewrite ``{posargs}`` substitution for absolute paths. (`#1095 <https://github.com/tox-dev/tox/issues/1095>`_)
- Correctly fail ``tox --notest`` when setup fails. (`#1097 <https://github.com/tox-dev/tox/issues/1097>`_)

.. _release-3-6-0-documentation:

Documentation
-------------

- Update Contributor Covenant URL to use https:// - by :user:`jdufresne`. (`#1082
  <https://github.com/tox-dev/tox/issues/1082>`_)
- Correct the capitalization of PyPI throughout the documentation - by :user:`jdufresne`. (`#1084
  <https://github.com/tox-dev/tox/issues/1084>`_)
- Link to related projects (Invoke and Nox) from the documentation - by :user:`theacodes`. (`#1088
  <https://github.com/tox-dev/tox/issues/1088>`_)

.. _release-3-6-0-packaging:

Packaging
---------

- Include the license file in the wheel distribution - by :user:`jdufresne`. (`#1083
  <https://github.com/tox-dev/tox/issues/1083>`_)

.. _release-3-5-3:

********************
 3.5.3 (2018-10-28)
********************

.. _release-3-5-3-fixed:

Fixed
-----

- Fix bug with incorrectly defactorized dependencies - by :user:`bartsanchez` (`#706
  <https://github.com/tox-dev/tox/issues/706>`_)
- do the same transformation to ``egg_info`` folders that ``pkg_resources`` does; this makes it possible for hyphenated
  names to use the ``develop-inst-noop`` optimization (cf. 910), which previously only worked with non-hyphenated egg
  names - by :user:`hashbrowncipher` (`#1051 <https://github.com/tox-dev/tox/issues/1051>`_)
- previously, if a project's ``setup.py --name`` emitted extra information to stderr, tox would capture it and consider
  it part of the project's name; now, emissions to stderr are printed to the console - by :user:`hashbrowncipher`
  (`#1052 <https://github.com/tox-dev/tox/issues/1052>`_)
- change the way we acquire interpreter information to make it compatible with ``jython`` interpreter, note to create
  jython envs one needs ``virtualenv > 16.0`` which will be released later :user:`gaborbernat` (`#1073
  <https://github.com/tox-dev/tox/issues/1073>`_)

.. _release-3-5-3-documentation:

Documentation
-------------

- document substitutions with additional content starting with a space cannot be alone on a line inside the ini file -
  by :user:`gaborbernat` (`#437 <https://github.com/tox-dev/tox/issues/437>`_)
- change the spelling of a single word from constrains to the proper word, constraints - by :user:`metasyn` (`#1061
  <https://github.com/tox-dev/tox/issues/1061>`_)
- Mention the minimum version required for ``commands_pre``/``commands_post`` support. (`#1071
  <https://github.com/tox-dev/tox/issues/1071>`_)

.. _release-3-5-2:

********************
 3.5.2 (2018-10-09)
********************

.. _release-3-5-2-added:

Added
-----

- level three verbosity (``-vvv``) show the packaging output - by :user:`gaborbernat` (`#1047
  <https://github.com/tox-dev/tox/issues/1047>`_)

.. _release-3-5-2-fixed:

Fixed
-----

- session packages are now put inside a numbered directory (instead of prefix numbering it, because pip fails when
  wheels are not named according to `PEP-491 <https://www.python.org/dev/peps/pep-0491/#id9>`_, and prefix numbering
  messes with this) - by :user:`gaborbernat` (`#1042 <https://github.com/tox-dev/tox/issues/1042>`_)

.. _release-3-5-1:

********************
 3.5.1 (2018-10-08)
********************

.. _release-3-5-1-fixed:

Fixed
-----

- fix regression with ``3.5.0``: specifying ``--installpkg`` raises ``AttributeError: 'str' object has no attribute
  'basename'`` (`#1042 <https://github.com/tox-dev/tox/issues/1042>`_)

.. _release-3-5-0:

********************
 3.5.0 (2018-10-08)
********************

.. _release-3-5-0-added:

Added
-----

- Added ``temp_dir`` folder configuration (defaults to ``{toxworkdir}/.tmp``) that contains tox temporary files. Package
  builds now create a hard link (if possible, otherwise copy - notably in case of Windows Python 2.7) to the built file,
  and feed that file downstream (e.g. for pip to install it). The hard link is removed at the end of the run (what it
  points though is kept inside ``distdir``). This ensures that a tox session operates on the same package it built, even
  if a parallel tox run builds another version. Note ``distdir`` will contain only the last built package in such cases.
  by :user:`gaborbernat` (`#1026 <https://github.com/tox-dev/tox/issues/1026>`_)

.. _release-3-5-0-fixed:

Fixed
-----

- intermittent failures with ``--parallel--safe-build``, instead of mangling with the file paths now uses a lock to make
  the package build operation thread safe and is now on by default (``--parallel--safe-build`` is now deprecated) - by
  :user:`gaborbernat` (`#1026 <https://github.com/tox-dev/tox/issues/1026>`_)

.. _release-3-5-0-documentation:

Documentation
-------------

- document tox environment recreate rules (:ref:`recreate`) - by :user:`gaborbernat` (`#93
  <https://github.com/tox-dev/tox/issues/93>`_)
- document inside the ``--help`` how to disable colorized output via the ``PY_COLORS`` operating system environment
  variable - by :user:`gaborbernat` (`#163 <https://github.com/tox-dev/tox/issues/163>`_)
- document all global tox flags and a more concise format to express default and type - by :user:`gaborbernat` (`#683
  <https://github.com/tox-dev/tox/issues/683>`_)
- document command line interface under the config section `cli
  <https://tox.readthedocs.io/en/latest/config.html?highlight=cli#cli>`_ - by :user:`gaborbernat` (`#829
  <https://github.com/tox-dev/tox/issues/829>`_)

.. _release-3-4-0:

********************
 3.4.0 (2018-09-20)
********************

.. _release-3-4-0-added:

Added
-----

- add ``commands_pre`` and ``commands_post`` that run before and after running the ``commands`` (setup runs always,
  commands only if setup succeeds, teardown always - all run until the first failing command) - by :user:`gaborbernat`
  (`#167 <https://github.com/tox-dev/tox/issues/167>`_)
- ``pyproject.toml`` config support initially by just inline the tox.ini under ``tool.tox.legacy_tox_ini`` key; config
  source priority order is ``pyproject.toml``, ``tox.ini`` and then ``setup.cfg`` - by :user:`gaborbernat` (`#814
  <https://github.com/tox-dev/tox/issues/814>`_)
- use the os environment variable ``TOX_SKIP_ENV`` to filter out tox environment names from the run list (set by
  ``envlist``) - by :user:`gaborbernat` (`#824 <https://github.com/tox-dev/tox/issues/824>`_)
- always set ``PIP_USER=0`` (do not install into the user site package, but inside the virtual environment created) and
  ``PIP_NO_DEPS=0`` (installing without dependencies can cause broken package installations) inside tox - by
  :user:`gaborbernat` (`#838 <https://github.com/tox-dev/tox/issues/838>`_)
- tox will inject some environment variables that to indicate a command is running within tox: ``TOX_WORK_DIR`` env var
  is set to the tox work directory, ``TOX_ENV_NAME`` is set to the current running tox environment name, ``TOX_ENV_DIR``
  is set to the current tox environments working dir - by :user:`gaborbernat` (`#847
  <https://github.com/tox-dev/tox/issues/847>`_)
- While running tox invokes various commands (such as building the package, pip installing dependencies and so on),
  these were printed in case they failed as Python arrays. Changed the representation to a shell command, allowing the
  users to quickly replicate/debug the failure on their own - by :user:`gaborbernat` (`#851
  <https://github.com/tox-dev/tox/issues/851>`_)
- skip missing interpreters value from the config file can now be overridden via the ``--skip-missing-interpreters`` cli
  flag - by :user:`gaborbernat` (`#903 <https://github.com/tox-dev/tox/issues/903>`_)
- keep additional environments config order when listing them - by :user:`gaborbernat` (`#921
  <https://github.com/tox-dev/tox/issues/921>`_)
- allow injecting config value inside the ini file dependent of the fact that we're connected to an interactive shell or
  not via exposing a ``{tty}`` substitution - by :user:`gaborbernat` (`#947
  <https://github.com/tox-dev/tox/issues/947>`_)
- do not build sdist if skip install is specified for the envs to be run - by :user:`gaborbernat` (`#974
  <https://github.com/tox-dev/tox/issues/974>`_)
- when verbosity level increases above two start passing through verbosity flags to pip - by :user:`gaborbernat` (`#982
  <https://github.com/tox-dev/tox/issues/982>`_)
- when discovering the interpreter to use check if the tox host Python matches and use that if so - by
  :user:`gaborbernat` (`#994 <https://github.com/tox-dev/tox/issues/994>`_)
- ``-vv`` will print out why a virtual environment is re-created whenever this operation is triggered - by
  :user:`gaborbernat` (`#1004 <https://github.com/tox-dev/tox/issues/1004>`_)

.. _release-3-4-0-fixed:

Fixed
-----

- add ``--exists-action w`` to default pip flags to handle better VCS dependencies (`pip documentation on this
  <https://pip.pypa.io/en/latest/reference/pip/#exists-action-option>`_) - by :user:`gaborbernat` (`#503
  <https://github.com/tox-dev/tox/issues/503>`_)
- instead of assuming the Python version from the base python name ask the interpreter to reveal the version for the
  ``ignore_basepython_conflict`` flag - by :user:`gaborbernat` (`#908 <https://github.com/tox-dev/tox/issues/908>`_)
- PEP-517 packaging fails with sdist already exists, fixed via ensuring the dist folder is empty before invoking the
  backend and `pypa/setuptools 1481 <https://github.com/pypa/setuptools/pull/1481>`_ - by :user:`gaborbernat` (`#1003
  <https://github.com/tox-dev/tox/issues/1003>`_)

.. _release-3-4-0-documentation:

Documentation
-------------

- clarify that ``python`` and ``pip`` refer to the virtual environments executable - by :user:`gaborbernat` (`#305
  <https://github.com/tox-dev/tox/issues/305>`_)
- add Sphinx and mkdocs example of generating documentation via tox - by :user:`gaborbernat` (`#374
  <https://github.com/tox-dev/tox/issues/374>`_)
- specify that ``setup.cfg`` tox configuration needs to be inside the ``tox:tox`` namespace - by :user:`gaborbernat`
  (`#545 <https://github.com/tox-dev/tox/issues/545>`_)

.. _release-3-3-0:

********************
 3.3.0 (2018-09-11)
********************

.. _release-3-3-0-added:

Added
-----

- `PEP-517 <https://www.python.org/dev/peps/pep-0517/>`_ source distribution support (create a ``.package`` virtual
  environment to perform build operations inside) by :user:`gaborbernat` (`#573
  <https://github.com/tox-dev/tox/issues/573>`_)
- `flit <https://flit.readthedocs.io>`_ support via implementing ``PEP-517`` by :user:`gaborbernat` (`#820
  <https://github.com/tox-dev/tox/issues/820>`_)
- packaging now is exposed as a hook via ``tox_package(session, venv)`` - by :user:`gaborbernat` (`#951
  <https://github.com/tox-dev/tox/issues/951>`_)

.. _release-3-3-0-changes:

Changes
-------

- Updated the VSTS build YAML to use the latest jobs and pools syntax - by :user:`davidstaheli` (`#955
  <https://github.com/tox-dev/tox/issues/955>`_)

.. _release-3-3-0-fixed:

Fixed
-----

- fix ``TOX_LIMITED_SHEBANG`` when running under python3 - by :user:`asottile` (`#931
  <https://github.com/tox-dev/tox/issues/931>`_)

.. _release-3-2-1:

********************
 3.2.1 (2018-08-10)
********************

.. _release-3-2-1-fixed:

Fixed
-----

- ``--parallel--safe-build`` no longer cleans up its folders (``distdir``, ``distshare``, ``log``). - by
  :user:`gaborbernat` (`#849 <https://github.com/tox-dev/tox/issues/849>`_)

.. _release-3-2-0:

********************
 3.2.0 (2018-08-10)
********************

.. _release-3-2-0-added:

Added
-----

- Switch pip invocations to use the module ``-m pip`` instead of direct invocation. This could help avoid some of the
  shebang limitations. - by :user:`gaborbernat` (`#935 <https://github.com/tox-dev/tox/issues/935>`_)
- Ability to specify package requirements for the tox run via the ``tox.ini`` (``tox`` section under key ``requires`` -
  PEP-508 style): can be used to specify both plugin requirements or build dependencies. - by :user:`gaborbernat` (`#783
  <https://github.com/tox-dev/tox/issues/783>`_)
- Allow one to run multiple tox instances in parallel by providing the ``--parallel--safe-build`` flag. - by
  :user:`gaborbernat` (`#849 <https://github.com/tox-dev/tox/issues/849>`_)

.. _release-3-1-3:

********************
 3.1.3 (2018-08-03)
********************

.. _release-3-1-3-added:

Added
-----

- Python version testenvs are now automatically detected instead of comparing against a hard-coded list of supported
  versions. This enables ``py38`` and eventually ``py39`` / ``py40`` / etc. to work without requiring an upgrade to
  ``tox``. As such, the following public constants are now deprecated (and scheduled for removal in ``tox`` 4.0:
  ``CPYTHON_VERSION_TUPLES``, ``PYPY_VERSION_TUPLES``, ``OTHER_PYTHON_INTERPRETERS``, and ``DEFAULT_FACTORS`` - by
  :user:`asottile` (`#914 <https://github.com/tox-dev/tox/issues/914>`_)

.. _release-3-1-3-fixed:

Fixed
-----

- A caching issue that caused the ``develop-inst-nodeps`` action, which reinstalls the package under test, to always run
  has been resolved. The ``develop-inst-noop`` action, which, as the name suggests, is a no-op, will now run unless
  there are changes to ``setup.py`` or ``setup.cfg`` files that have not been reflected - by :user:`stephenfin` (`#909
  <https://github.com/tox-dev/tox/issues/909>`_)

.. _release-3-1-3-documentation:

Documentation
-------------

- Add a system overview section on the index page that explains briefly how tox works - by :user:`gaborbernat`. (`#867
  <https://github.com/tox-dev/tox/issues/867>`_)

.. _release-3-1-2:

********************
 3.1.2 (2018-07-12)
********************

.. _release-3-1-2-fixed:

Fixed
-----

- Revert "Fix bug with incorrectly defactorized dependencies (`#772 <https://github.com/tox-dev/tox/issues/772>`_)" due
  to a regression (`(#799) <https://github.com/tox-dev/tox/issues/899>`_) - by :user:`obestwalter`

.. _release-3-1-1:

********************
 3.1.1 (2018-07-09)
********************

.. _release-3-1-1-fixed:

Fixed
-----

- PyPI documentation for ``3.1.0`` is broken. Added test to check for this, and fix it by :user:`gaborbernat`. (`#879
  <https://github.com/tox-dev/tox/issues/879>`_)

.. _release-3-1-0:

********************
 3.1.0 (2018-07-08)
********************

.. _release-3-1-0-added:

Added
-----

- Add support for multiple PyPy versions using default factors. This allows you to use, for example, ``pypy27`` knowing
  that the correct interpreter will be used by default - by :user:`stephenfin` (`#19
  <https://github.com/tox-dev/tox/issues/19>`_)
- Add support to explicitly invoke interpreter directives for environments with long path lengths. In the event that
  ``tox`` cannot invoke scripts with a system-limited shebang (e.x. a Linux host running a Jenkins Pipeline), a user can
  set the environment variable ``TOX_LIMITED_SHEBANG`` to workaround the system's limitation (e.x. ``export
  TOX_LIMITED_SHEBANG=1``) - by :user:`jdknight` (`#794 <https://github.com/tox-dev/tox/issues/794>`_)
- introduce a constants module to be used internally and as experimental API - by :user:`obestwalter` (`#798
  <https://github.com/tox-dev/tox/issues/798>`_)
- Make ``py2`` and ``py3`` aliases also resolve via ``py`` on windows by :user:`asottile`. This enables the following
  things: ``tox -e py2`` and ``tox -e py3`` work on windows (they already work on posix); and setting
  ``basepython=python2`` or ``basepython=python3`` now works on windows. (`#856
  <https://github.com/tox-dev/tox/issues/856>`_)
- Replace the internal version parsing logic from the not well tested `PEP-386
  <https://www.python.org/dev/peps/pep-0386/>`_ parser for the more general `PEP-440
  <https://www.python.org/dev/peps/pep-0440/>`_. `packaging >= 17.1 <https://pypi.org/project/packaging/>`_ is now an
  install dependency by :user:`gaborbernat`. (`#860 <https://github.com/tox-dev/tox/issues/860>`_)

.. _release-3-1-0-changes:

Changes
-------

- make the already existing implicit API explicit - by :user:`obestwalter` (`#800
  <https://github.com/tox-dev/tox/issues/800>`_)
- tweak codecov settings via .codecov.yml - by :user:`obestwalter` (`#802 <https://github.com/tox-dev/tox/issues/802>`_)

.. _release-3-1-0-fixed:

Fixed
-----

- Add ``ignore_basepython_conflict``, which determines whether conflicting ``basepython`` settings for environments
  containing default factors, such as ``py27`` or ``django18-py35``, should be ignored or result in warnings. This was a
  common source of misconfiguration and is rarely, if ever, desirable from a user perspective - by :user:`stephenfin`
  (`#477 <https://github.com/tox-dev/tox/issues/477>`_)
- Fix bug with incorrectly defactorized dependencies (deps passed to pip were not de-factorized) - by
  :user:`bartsanchez` (`#706 <https://github.com/tox-dev/tox/issues/706>`_)

.. _release-3-1-0-documentation:

Documentation
-------------

- extend the plugin documentation and make lot of small fixes and improvements - by :user:`obestwalter` (`#797
  <https://github.com/tox-dev/tox/issues/797>`_)
- tidy up tests - remove unused fixtures, update old cinstructs, etc. - by :user:`obestwalter` (`#799
  <https://github.com/tox-dev/tox/issues/799>`_)
- Various improvements to documentation: open browser once documentation generation is done, show Github/Travis info on
  documentation page, remove duplicate header for changelog, generate unreleased news as DRAFT on top of changelog, make
  the changelog page more compact and readable (width up to 1280px) by :user:`gaborbernat` (`#859
  <https://github.com/tox-dev/tox/issues/859>`_)
- improve tox quickstart and corresponding tests - by :user:`obestwalter` (`#801
  <https://github.com/tox-dev/tox/issues/801>`_)

.. _release-3-1-0-packaging:

Packaging
---------

- filter out unwanted files in package - by :user:`obestwalter` (`#754 <https://github.com/tox-dev/tox/issues/754>`_)

.. _release-3-0-0:

********************
 3.0.0 (2018-04-02)
********************

.. _release-3-0-0-added:

Added
-----

- ``tox`` displays exit code together with ``InvocationError`` - by :user:`blueyed` and :user:`ederag`. (`#290
  <https://github.com/tox-dev/tox/issues/290>`_)
- Hint for possible signal upon ``InvocationError``, on posix systems - by :user:`ederag` and :user:`asottile`. (`#766
  <https://github.com/tox-dev/tox/issues/766>`_)
- Add a ``-q`` option to progressively silence tox's output. For each time you specify ``-q`` to tox, the output
  provided by tox reduces. This option allows you to see only your command output without the default verbosity of what
  tox is doing. This also counter-acts usage of ``-v``. For example, running ``tox -v -q ...`` will provide you with the
  default verbosity. ``tox -vv -q`` is equivalent to ``tox -v``. By :user:`sigmavirus24` (`#256
  <https://github.com/tox-dev/tox/issues/256>`_)
- add support for negated factor conditions, e.g. ``!dev: production_log`` - by :user:`jurko-gospodnetic` (`#292
  <https://github.com/tox-dev/tox/issues/292>`_)
- Headings like ``installed: <packages>`` will not be printed if there is no output to display after the :, unless
  verbosity is set. By :user:`cryvate` (`#601 <https://github.com/tox-dev/tox/issues/601>`_)
- Allow spaces in command line options to pip in deps. Where previously only ``deps=-rreq.txt`` and
  ``deps=--requirement=req.txt`` worked, now also ``deps=-r req.txt`` and ``deps=--requirement req.txt`` work - by
  :user:`cryvate` (`#668 <https://github.com/tox-dev/tox/issues/668>`_)
- drop Python ``2.6`` and ``3.3`` support: ``setuptools`` dropped supporting these, and as we depend on it we'll follow
  up with doing the same (use ``tox <= 2.9.1`` if you still need this support) - by :user:`gaborbernat` (`#679
  <https://github.com/tox-dev/tox/issues/679>`_)
- Add tox_runenvreport as a possible plugin, allowing the overriding of the default behavior to execute a command to get
  the installed packages within a virtual environment - by :user:`tonybaloney` (`#725
  <https://github.com/tox-dev/tox/issues/725>`_)
- Forward ``PROCESSOR_ARCHITECTURE`` by default on Windows to fix ``platform.machine()``. (`#740
  <https://github.com/tox-dev/tox/issues/740>`_)

.. _release-3-0-0-changes:

Changes
-------

- touched up ``interpreters.py`` code and added some missing tests for it - by :user:`jurko-gospodnetic` (`#708
  <https://github.com/tox-dev/tox/issues/708>`_)
- The ``PYTHONDONTWRITEBYTECODE`` environment variable is no longer unset - by :user:`stephenfin`. (`#744
  <https://github.com/tox-dev/tox/issues/744>`_)

.. _release-3-0-0-fixed:

Fixed
-----

- Write directly to stdout buffer if possible to prevent str vs bytes issues - by :user:`asottile` (`#426
  <https://github.com/tox-dev/tox/issues/426>`_)
- fix #672 reporting to json file when skip-missing-interpreters option is used - by :user:`r2dan` (`#672
  <https://github.com/tox-dev/tox/issues/672>`_)
- avoid ``Requested Python version (X.Y) not installed`` stderr output when a Python environment is looked up using the
  ``py`` Python launcher on Windows and the environment is not found installed on the system - by
  :user:`jurko-gospodnetic` (`#692 <https://github.com/tox-dev/tox/issues/692>`_)
- Fixed an issue where invocation of tox from the Python package, where invocation errors (failed actions) occur results
  in a change in the sys.stdout stream encoding in Python 3.x. New behavior is that sys.stdout is reset back to its
  original encoding after invocation errors - by :user:`tonybaloney` (`#723
  <https://github.com/tox-dev/tox/issues/723>`_)
- The reading of command output sometimes failed with ``IOError: [Errno 0] Error`` on Windows, this was fixed by using a
  simpler method to update the read buffers. - by :user:`fschulze` (`#727 <https://github.com/tox-dev/tox/issues/727>`_)
- (only affected rc releases) fix up tox.cmdline to be callable without args - by :user:`gaborbernat`. (`#773
  <https://github.com/tox-dev/tox/issues/773>`_)
- (only affected rc releases) Revert breaking change of tox.cmdline not callable with no args - by :user:`gaborbernat`.
  (`#773 <https://github.com/tox-dev/tox/issues/773>`_)
- (only affected rc releases) fix #755 by reverting the ``cmdline`` import to the old location and changing the entry
  point instead - by :user:`fschulze` (`#755 <https://github.com/tox-dev/tox/issues/755>`_)
- Running ``tox`` without a ``setup.py`` now has a more friendly error message and gives troubleshooting suggestions -
  by :user:`Volcyy`. (`#331 <https://github.com/tox-dev/tox/issues/331>`_)
- Fix pycodestyle (formerly pep8) errors E741 (ambiguous variable names, in this case, 'l's) and remove ignore of this
  error in tox.ini - by :user:`cryvate` (`#663 <https://github.com/tox-dev/tox/issues/663>`_)

.. _release-3-0-0-documentation:

Documentation
-------------

- Change favicon to the vector beach ball - by :user:`hazalozturk` (`#748 <https://github.com/tox-dev/tox/issues/748>`_)
- Change sphinx theme to alabaster and add logo/favicon - by :user:`hazalozturk` (`#639
  <https://github.com/tox-dev/tox/issues/639>`_)

.. _release-3-0-0rc4:

***********************
 3.0.0rc4 (2018-03-23)
***********************

.. _release-3-0-0rc3:

***********************
 3.0.0rc3 (2018-03-22)
***********************

.. _release-3-0-0rc3-fixed:

Fixed
-----

- Revert breaking change of tox.cmdline not callable with no args - by :user:`gaborbernat`. (`#773
  <https://github.com/tox-dev/tox/issues/773>`_)

.. _release-3-0-0rc2:

***********************
 3.0.0rc2 (2018-03-03)
***********************

.. _release-3-0-0rc2-added:

Added
-----

- ``tox`` displays exit code together with ``InvocationError`` - by :user:`blueyed` and :user:`ederag`. (`#290
  <https://github.com/tox-dev/tox/issues/290>`_)
- Hint for possible signal upon ``InvocationError``, on posix systems - by :user:`ederag` and :user:`asottile`. (`#766
  <https://github.com/tox-dev/tox/issues/766>`_)

.. _release-3-0-0rc2-fixed:

Fixed
-----

- fix #755 by reverting the ``cmdline`` import to the old location and changing the entry point instead - by
  :user:`fschulze` (`#755 <https://github.com/tox-dev/tox/issues/755>`_)

.. _release-3-0-0rc2-documentation:

Documentation
-------------

- Change favicon to the vector beach ball - by :user:`hazalozturk` (`#748 <https://github.com/tox-dev/tox/issues/748>`_)

.. _release-3-0-0rc1:

***********************
 3.0.0rc1 (2018-01-28)
***********************

.. _release-3-0-0rc1-added:

Added
-----

- Add a ``-q`` option to progressively silence tox's output. For each time you specify ``-q`` to tox, the output
  provided by tox reduces. This option allows you to see only your command output without the default verbosity of what
  tox is doing. This also counter-acts usage of ``-v``. For example, running ``tox -v -q ...`` will provide you with the
  default verbosity. ``tox -vv -q`` is equivalent to ``tox -v``. By :user:`sigmavirus24` (`#256
  <https://github.com/tox-dev/tox/issues/256>`_)
- add support for negated factor conditions, e.g. ``!dev: production_log`` - by :user:`jurko-gospodnetic` (`#292
  <https://github.com/tox-dev/tox/issues/292>`_)
- Headings like ``installed: <packages>`` will not be printed if there is no output to display after the :, unless
  verbosity is set. By :user:`cryvate` (`#601 <https://github.com/tox-dev/tox/issues/601>`_)
- Allow spaces in command line options to pip in deps. Where previously only ``deps=-rreq.txt`` and
  ``deps=--requirement=req.txt`` worked, now also ``deps=-r req.txt`` and ``deps=--requirement req.txt`` work - by
  :user:`cryvate` (`#668 <https://github.com/tox-dev/tox/issues/668>`_)
- drop Python ``2.6`` and ``3.3`` support: ``setuptools`` dropped supporting these, and as we depend on it we'll follow
  up with doing the same (use ``tox <= 2.9.1`` if you still need this support) - by :user:`gaborbernat` (`#679
  <https://github.com/tox-dev/tox/issues/679>`_)
- Add tox_runenvreport as a possible plugin, allowing the overriding of the default behavior to execute a command to get
  the installed packages within a virtual environment - by :user:`tonybaloney` (`#725
  <https://github.com/tox-dev/tox/issues/725>`_)
- Forward ``PROCESSOR_ARCHITECTURE`` by default on Windows to fix ``platform.machine()``. (`#740
  <https://github.com/tox-dev/tox/issues/740>`_)

.. _release-3-0-0rc1-changes:

Changes
-------

- The ``PYTHONDONTWRITEBYTECODE`` environment variable is no longer unset - by :user:`stephenfin`. (`#744
  <https://github.com/tox-dev/tox/issues/744>`_)

.. _release-3-0-0rc1-fixed:

Fixed
-----

- Write directly to stdout buffer if possible to prevent str vs bytes issues - by :user:`asottile` (`#426
  <https://github.com/tox-dev/tox/issues/426>`_)
- fix #672 reporting to json file when skip-missing-interpreters option is used by :user:`r2dan` (`#672
  <https://github.com/tox-dev/tox/issues/672>`_)
- avoid ``Requested Python version (X.Y) not installed`` stderr output when a Python environment is looked up using the
  ``py`` Python launcher on Windows and the environment is not found installed on the system - by
  :user:`jurko-gospodnetic` (`#692 <https://github.com/tox-dev/tox/issues/692>`_)
- Fixed an issue where invocation of Tox from the Python package, where invocation errors (failed actions) occur results
  in a change in the sys.stdout stream encoding in Python 3.x. New behavior is that sys.stdout is reset back to its
  original encoding after invocation errors - by :user:`tonybaloney` (`#723
  <https://github.com/tox-dev/tox/issues/723>`_)
- The reading of command output sometimes failed with ``IOError: [Errno 0] Error`` on Windows, this was fixed by using a
  simpler method to update the read buffers. - by :user:`fschulze` (`#727 <https://github.com/tox-dev/tox/issues/727>`_)
- Running ``tox`` without a ``setup.py`` now has a more friendly error message and gives troubleshooting suggestions -
  by :user:`Volcyy`. (`#331 <https://github.com/tox-dev/tox/issues/331>`_)

.. _release-3-0-0rc1-documentation:

Documentation
-------------

- Change sphinx theme to alabaster and add logo/favicon - by :user:`hazalozturk` (`#639
  <https://github.com/tox-dev/tox/issues/639>`_)

.. _release-2-9-1:

********************
 2.9.1 (2017-09-29)
********************

.. _release-2-9-1-changes:

Changes
-------

- integrated new release process and fixed changelog rendering for pypi.org - by :user:`obestwalter`.

.. _release-2-9-0:

********************
 2.9.0 (2017-09-29)
********************

.. _release-2-9-0-added:

Added
-----

- ``tox --version`` now shows information about all registered plugins - by :user:`obestwalter` (`#544
  <https://github.com/tox-dev/tox/issues/544>`_)

.. _release-2-9-0-changes:

Changes
-------

- `#635 <https://github.com/tox-dev/tox/issues/635>`_ inherit from correct exception - by :user:`obestwalter` (`#635
  <https://github.com/tox-dev/tox/issues/635>`_).
- spelling and escape sequence fixes - by :user:`scoop` (`#637 <https://github.com/tox-dev/tox/issues/637>`_ and `#638
  <https://github.com/tox-dev/tox/issues/638>`_).

.. _release-2-9-0-fixed:

Fixed
-----

- ``skip_install`` overrides ``usedevelop`` (``usedevelop`` is an option to choose the installation type if the package
  is installed and ``skip_install`` determines if it should be installed at all) - by :user:`ferdonline` (`#571
  <https://github.com/tox-dev/tox/issues/571>`_)

.. _release-2-9-0-documentation:

Documentation
-------------

- add a badge to show build status of documentation on readthedocs.io - by :user:`obestwalter`.
- add `towncrier <https://github.com/hawkowl/towncrier>`_ to allow adding changelog entries with the pull requests
  without generating merge conflicts; with this release notes are now grouped into four distinct collections:
  ``Features``, ``Bugfixes``, ``Improved Documentation`` and ``Deprecations and Removals``. (`#614
  <https://github.com/tox-dev/tox/issues/614>`_)

.. _release-2-9-0rc1:

***********************
 2.9.0rc1 (2017-09-14)
***********************

.. _release-2-9-0rc1-added:

Added
-----

- ``tox --version`` now shows information about all registered plugins - by obestwalter (`#544
  <https://github.com/tox-dev/tox/issues/544>`_)

.. _release-2-9-0rc1-fixed:

Fixed
-----

- ``skip_install`` overrides ``usedevelop`` (``usedevelop`` is an option to choose the installation type if the package
  is installed and ``skip_install`` determines if it should be installed at all) - by ferdonline (`#571
  <https://github.com/tox-dev/tox/issues/571>`_)

.. _release-2-9-0rc1-documentation:

Documentation
-------------

- add `towncrier <https://github.com/hawkowl/towncrier>`_ to allow adding changelog entries with the pull requests
  without generating merge conflicts; with this release notes are now grouped into four distinct collections:
  ``Features``, ``Bugfixes``, ``Improved Documentation`` and ``Deprecations and Removals``. (`#614
  <https://github.com/tox-dev/tox/issues/614>`_)

.. _release-2-8-2:

********************
 2.8.2 (2017-10-09)
********************

.. _release-2-8-2-changes:

Changes
-------

- `#466 <https://github.com/tox-dev/tox/issues/466>`_: stop env var leakage if popen failed with resultjson or redirect

.. _release-2-8-1:

********************
 2.8.1 (2017-09-04)
********************

.. _release-2-8-1-changes:

Changes
-------

- `pull request 599 <https://github.com/tox-dev/tox/pull/599>`_: fix problems with implementation of `#515
  <https://github.com/tox-dev/tox/issues/515>`_. Substitutions from other sections were not made anymore if they were
  not in ``envlist``. Thanks to Clark Boylan (:user:`cboylan`) for helping to get this fixed (`pull request 597
  <https://github.com/tox-dev/tox/pull/597>`_).

.. _release-2-8-0:

********************
 2.8.0 (2017-09-01)
********************

.. _release-2-8-0-changes:

Changes
-------

- `#301 <https://github.com/tox-dev/tox/issues/301>`_: Expand nested substitutions in ``tox.ini``. Thanks :user:`vlaci`.
  Thanks to Eli Collins (:user:`eli-collins`) for creating a reproducer.
- `#429 <https://github.com/tox-dev/tox/issues/429>`_: Forward ``MSYSTEM`` by default on Windows. Thanks Marius Gedminas
  (:user:`mgedmin`) for reporting this.
- `#484 <https://github.com/tox-dev/tox/issues/484>`_: Renamed ``py.test`` to ``pytest`` throughout the project. Thanks
  Slam (:user:`3lnc`).
- `#504 <https://github.com/tox-dev/tox/issues/504>`_: With ``-a``: do not show additional environments header if there
  are none. Thanks :user:`rndr`.
- `#515 <https://github.com/tox-dev/tox/issues/515>`_: Don't require environment variables in test environments where
  they are not used. Thanks André Caron (:user:`AndreLouisCaron`).
- `#517 <https://github.com/tox-dev/tox/issues/517>`_: Forward ``NUMBER_OF_PROCESSORS`` by default on Windows to fix
  ``multiprocessor.cpu_count()``. Thanks André Caron (:user:`AndreLouisCaron`).
- `#518 <https://github.com/tox-dev/tox/issues/518>`_: Forward ``USERPROFILE`` by default on Windows. Thanks André Caron
  (:user:`AndreLouisCaron`).
- `pull request 528 <https://github.com/tox-dev/tox/pull/528>`_: Fix some of the warnings displayed by pytest 3.1.0.
  Thanks Bruno Oliveira (:user:`nicoddemus`).
- `pull request 547 <https://github.com/tox-dev/tox/pull/547>`_: Add regression test for `#137
  <https://github.com/tox-dev/tox/issues/137>`_. Thanks Martin Andrysík (:user:`sifuraz`).
- `pull request 553 <https://github.com/tox-dev/tox/pull/553>`_: Add an XFAIL test to reproduce upstream bug `#203
  <https://github.com/tox-dev/tox/issues/203>`_. Thanks Bartolomé Sánchez Salado (:user:`bartsanchez`).
- `pull request 580 <https://github.com/tox-dev/tox/pull/580>`_: Do not ignore Sphinx warnings anymore. Thanks Bernát
  Gábor (:user:`gaborbernat`).
- `pull request 588 <https://github.com/tox-dev/tox/pull/588>`_: Run pytest with xfail_strict and adapt affected tests.

.. _release-2-8-0-fixed:

Fixed
-----

- `#326 <https://github.com/tox-dev/tox/issues/326>`_: Fix ``OSError`` 'Not a directory' when creating env on Jython
  2.7.0. Thanks Nick Douma (:user:`LordGaav`).
- `pull request 556 <https://github.com/tox-dev/tox/pull/556>`_: Report more meaningful errors on why virtualenv
  creation failed. Thanks :user:`vlaci`. Also thanks to Igor Sadchenko (:user:`igor-sadchenko`) for pointing out a
  problem with that PR before it hit the masses ☺

.. _release-2-8-0-documentation:

Documentation
-------------

- `#276 <https://github.com/tox-dev/tox/issues/276>`_: Remove easy_install from docs (TL;DR: use pip). Thanks Martin
  Andrysík (:user:`sifuraz`).
- `#315 <https://github.com/tox-dev/tox/issues/315>`_: add ``--help`` and ``--version`` to helptox-quickstart. Thanks
  :user:`vlaci`.
- `#449 <https://github.com/tox-dev/tox/issues/449>`_: add multi platform example to the docs. Thanks Aleks Bunin
  (:user:`sashkab`) and :user:`rndr`.
- `pull request 575 <https://github.com/tox-dev/tox/pull/575>`_: Add announcement doc to end all announcement docs
  (using only ``CHANGELOG`` and Github issues since 2.5 already).
- `pull request 585 <https://github.com/tox-dev/tox/pull/585>`_: Expand documentation to explain pass through of flags
  from deps to pip (e.g. ``-rrequirements.txt``, ``-cconstraints.txt``). Thanks Alexander Loechel (:user:`loechel`).

.. _release-2-8-0-packaging:

Packaging
---------

- `#474 <https://github.com/tox-dev/tox/issues/474>`_: Start using setuptools_scm for tag based versioning.

.. _release-2-8-0rc2:

***********************
 2.8.0rc2 (2017-08-26)
***********************

.. _release-2-8-0rc1:

***********************
 2.8.0rc1 (2017-08-13)
***********************

.. _release-2-7-0:

********************
 2.7.0 (2017-04-02)
********************

.. _release-2-7-0-changes:

Changes
-------

- `pull request 450 <https://github.com/tox-dev/tox/pull/450>`_: Stop after the first installdeps and first testenv
  create hooks succeed. This changes the default behavior of ``tox_testenv_create`` and ``tox_testenv_install_deps`` to
  not execute other registered hooks when the first hook returns a result that is not ``None``. Thanks Anthony Sottile
  (:user:`asottile`).
- `#271 <https://github.com/tox-dev/tox/issues/271>`_ and `#464 <https://github.com/tox-dev/tox/issues/464>`_: Improve
  environment information for users. New command line parameter: ``-a`` show **all** defined environments - not just the
  ones defined in (or generated from) envlist. New verbosity settings for ``-l`` and ``-a``: show user defined
  descriptions of the environments. This also works for generated environments from factors by concatenating factor
  descriptions into a complete description. Note that for backwards compatibility with scripts using the output of
  ``-l`` it's output remains unchanged. Thanks Bernát Gábor (:user:`gaborbernat`).
- `#431 <https://github.com/tox-dev/tox/issues/431>`_: Add 'LANGUAGE' to default passed environment variables. Thanks
  Paweł Adamczak (:user:`pawelad`).
- `#455 <https://github.com/tox-dev/tox/issues/455>`_: Add a Vagrantfile with a customized Arch Linux box for local
  testing. Thanks Oliver Bestwalter (:user:`obestwalter`).
- `#446 <https://github.com/tox-dev/tox/issues/446>`_: (infrastructure) Travis CI tests for tox now also run on OS X
  now. Thanks Jason R. Coombs (:user:`jaraco`).

.. _release-2-7-0-fixed:

Fixed
-----

- `#454 <https://github.com/tox-dev/tox/issues/454>`_: Revert `pull request 407
  <https://github.com/tox-dev/tox/pull/407>`_, empty commands is not treated as an error. Thanks Anthony Sottile
  (:user:`asottile`).

.. _release-2-7-0-packaging:

Packaging
---------

- `#464 <https://github.com/tox-dev/tox/issues/464>`_: Fix incorrect egg-info location for modified package_dir in
  setup.py. Thanks Selim Belhaouane (:user:`selimb`).

.. _release-2-6-0:

********************
 2.6.0 (2017-02-04)
********************

.. _release-2-6-0-added:

Added
-----

- add "alwayscopy" config option to instruct virtualenv to always copy files instead of symlinking. Thanks Igor Duarte
  Cardoso (:user:`igordcard`).
- add Python 3.6 to envlist and CI. Thanks Andrii Soldatenko (:user:`andriisoldatenko`).

.. _release-2-6-0-changes:

Changes
-------

- pass setenv variables to setup.py during a usedevelop install. Thanks Eli Collins (:user:`eli-collins`).
- replace all references to testrun.org with readthedocs ones. Thanks Oliver Bestwalter (:user:`obestwalter`).

.. _release-2-6-0-fixed:

Fixed
-----

- fix `#323 <https://github.com/tox-dev/tox/issues/323>`_ by avoiding virtualenv14 is not used on py32 (although we
  don't officially support py32). Thanks Jason R. Coombs (:user:`jaraco`).
- fix glob resolution from TOX_TESTENV_PASSENV env variable Thanks Allan Feldman (:user:`a-feld`).

.. _release-2-5-0:

********************
 2.5.0 (2016-11-16)
********************

.. _release-2-5-0-added:

Added
-----

- add support for py36 and py37 and add py36-dev and py37(nightly) to travis builds of tox. Thanks John Vandenberg.
- add {:} substitution, which is replaced with os-specific path separator, thanks Lukasz Rogalski.

.. _release-2-5-0-changes:

Changes
-------

- slightly backward incompatible: fix `#310 <https://github.com/tox-dev/tox/issues/310>`_: the {posargs} substitution
  now properly preserves the tox command line positional arguments. Positional arguments with spaces are now properly
  handled. NOTE: if your tox invocation previously used extra quoting for positional arguments to work around `#310
  <https://github.com/tox-dev/tox/issues/310>`_, you need to remove the quoting. Example: tox -- "'some string'" # has
  to now be written simply as tox -- "some string" thanks holger krekel. You can set ``minversion = 2.5.0`` in the
  ``[tox]`` section of ``tox.ini`` to make sure people using your tox.ini use the correct version.
- make "-h" and "--help-ini" options work even if there is no tox.ini, thanks holger krekel.
- output from install command in verbose (-vv) mode is now printed to console instead of being redirected to file,
  thanks Lukasz Rogalski

.. _release-2-5-0-fixed:

Fixed
-----

- fix `#359 <https://github.com/tox-dev/tox/issues/359>`_: add COMSPEC to default passenv on windows. Thanks
  :user:`anthrotype`.
- fix `#348 <https://github.com/tox-dev/tox/issues/348>`_: add py2 and py3 as default environments pointing to "python2"
  and "python3" basepython executables. Also fix `#347 <https://github.com/tox-dev/tox/issues/347>`_ by updating the
  list of default envs in the tox basic example. Thanks Tobias McNulty.
- fix `#305 <https://github.com/tox-dev/tox/issues/305>`_: ``downloadcache`` test env config is now ignored as pip-8
  does caching by default. Thanks holger krekel.
- fix `#399 <https://github.com/tox-dev/tox/issues/399>`_. Make sure {envtmpdir} is created if it doesn't exist at the
  start of a testenvironment run. Thanks Manuel Jacob.
- fix `#316 <https://github.com/tox-dev/tox/issues/316>`_: Lack of commands key in ini file is now treated as an error.
  Reported virtualenv status is 'nothing to do' instead of 'commands succeeded', with relevant error message displayed.
  Thanks Lukasz Rogalski.

.. _release-2-4-1:

********************
 2.4.1 (2016-10-12)
********************

.. _release-2-4-1-fixed:

Fixed
-----

- fix `#380 <https://github.com/tox-dev/tox/issues/380>`_: properly perform substitution again. Thanks Ian Cordasco.

.. _release-2-4-0:

********************
 2.4.0 (2016-10-12)
********************

.. _release-2-4-0-added:

Added
-----

- addresses `#66 <https://github.com/tox-dev/tox/issues/66>`_: add --workdir option to override where tox stores its
  ".tox" directory and all of the virtualenv environment. Thanks Danring.
- new list_dependencies_command to influence how tox determines which dependencies are installed in a testenv.
- added the "extras" environment option to specify the extras to use when doing the sdist or develop install.
  Contributed by Alex Grönholm.

.. _release-2-4-0-changes:

Changes
-------

- remove PYTHONPATH from environment during the install phase because a tox-run should not have hidden dependencies and
  the test commands will also not see a PYTHONPATH. If this causes unforeseen problems it may be reverted in a bugfix
  release. Thanks Jason R. Coombs.
- (experimental) New feature: When a search for a config file fails, tox tries loading setup.cfg with a section prefix
  of "tox".

.. _release-2-4-0-fixed:

Fixed
-----

- fix `#375 <https://github.com/tox-dev/tox/issues/375>`_, fix `#330 <https://github.com/tox-dev/tox/issues/330>`_: warn
  against tox-setup.py integration as "setup.py test" should really just test with the current interpreter. Thanks Ronny
  Pfannschmidt.
- fix `#302 <https://github.com/tox-dev/tox/issues/302>`_: allow cross-testenv substitution where we substitute with
  ``{x,y}`` generative syntax. Thanks Andrew Pashkin.
- fix `#212 <https://github.com/tox-dev/tox/issues/212>`_: allow escaping curly brace chars "\{" and "\}" if you need
  the chars "{" and "}" to appear in your commands or other ini values. Thanks John Vandenberg.
- fix `#275 <https://github.com/tox-dev/tox/issues/275>`_: Introduce hooks ``tox_runtest_pre`` and ``tox_runtest_post``
  which run before and after the tests of a venv, respectively. Thanks to Matthew Schinckel and itxaka serrano.
- fix `#317 <https://github.com/tox-dev/tox/issues/317>`_: evaluate minversion before tox config is parsed completely.
  Thanks Sachi King for the PR.

.. _release-2-4-0-documentation:

Documentation
-------------

- fix `#352 <https://github.com/tox-dev/tox/issues/352>`_: prevent a configuration where envdir==toxinidir and refine
  docs to warn people about changing "envdir". Thanks Oliver Bestwalter and holger krekel.
- close `#66 <https://github.com/tox-dev/tox/issues/66>`_: add documentation to jenkins page on how to avoid "too long
  shebang" lines when calling pip from tox. Note that we can not use "python -m pip install X" by default because the
  latter adds the CWD and pip will think X is installed if it is there. "pip install X" does not do that.

.. _release-2-4-0-deprecated:

Deprecated
----------

- use pytest-catchlog instead of pytest-capturelog (latter is not maintained, uses deprecated pytest API)

.. _release-2-4-0-packaging:

Packaging
---------

- introduce per-venv list_dependencies_command which defaults to "pip freeze" to obtain the list of installed packages.
  Thanks Ted Shaw, Holger Krekel.

.. _release-2-3-2:

********************
 2.3.2 (2016-02-11)
********************

.. _release-2-3-2-fixed:

Fixed
-----

- fix `#314 <https://github.com/tox-dev/tox/issues/314>`_: fix command invocation with .py scripts on windows.
- fix `#279 <https://github.com/tox-dev/tox/issues/279>`_: allow cross-section substitution when the value contains
  posargs. Thanks Sachi King for the PR.

.. _release-2-3-1:

********************
 2.3.1 (2015-12-14)
********************

.. _release-2-3-1-fixed:

Fixed
-----

- fix `#294 <https://github.com/tox-dev/tox/issues/294>`_: re-allow cross-section substitution for setenv.

.. _release-2-3-0:

********************
 2.3.0 (2015-12-09)
********************

.. _release-2-3-0-added:

Added
-----

- allow "#" in commands. This is slightly incompatible with commands sections that used a comment after a "\" line
  continuation. Thanks David Stanek for the PR.
- introduce experimental tox_testenv_create(venv, action) and tox_testenv_install_deps(venv, action) hooks to allow
  plugins to do additional work on creation or installing deps. These hooks are experimental mainly because of the
  involved "venv" and session objects whose current public API is not fully guaranteed.

.. _release-2-3-0-changes:

Changes
-------

- internal: push some optional object creation into tests because tox core doesn't need it.

.. _release-2-3-0-fixed:

Fixed
-----

- fix `#285 <https://github.com/tox-dev/tox/issues/285>`_: make setenv processing fully lazy to fix regressions of
  tox-2.2.X and so that we can now have testenv attributes like "basepython" depend on environment variables that are
  set in a setenv section. Thanks Nelfin for some tests and initial work on a PR.
- fix `#289 <https://github.com/tox-dev/tox/issues/289>`_: fix build_sphinx target, thanks Barry Warsaw.
- fix `#252 <https://github.com/tox-dev/tox/issues/252>`_: allow environment names with special characters. Thanks
  Julien Castets for initial PR and patience.

.. _release-2-3-0-deprecated:

Deprecated
----------

- DEPRECATE use of "indexservers" in tox.ini. It complicates the internal code and it is recommended to rather use the
  devpi system for managing indexes for pip.

.. _release-2-2-1:

********************
 2.2.1 (2015-12-09)
********************

.. _release-2-2-1-fixed:

Fixed
-----

- fix bug where {envdir} substitution could not be used in setenv if that env value is then used in {basepython}. Thanks
  Florian Bruhin.

.. _release-2-2-0:

********************
 2.2.0 (2015-11-11)
********************

.. _release-2-2-0-fixed:

Fixed
-----

- fix `#265 <https://github.com/tox-dev/tox/issues/265>`_ and add LD_LIBRARY_PATH to passenv on linux by default because
  otherwise the python interpreter might not start up in certain configurations (redhat software collections). Thanks
  David Riddle.
- fix `#246 <https://github.com/tox-dev/tox/issues/246>`_: fix regression in config parsing by reordering such that
  {envbindir} can be used again in tox.ini. Thanks Olli Walsh.
- fix `#99 <https://github.com/tox-dev/tox/issues/99>`_: the {env:...} substitution now properly uses environment
  settings from the ``setenv`` section. Thanks Itxaka Serrano.
- fix `#281 <https://github.com/tox-dev/tox/issues/281>`_: make --force-dep work when urls are present in dependency
  configs. Thanks Glyph Lefkowitz for reporting.
- fix `#174 <https://github.com/tox-dev/tox/issues/174>`_: add new ``ignore_outcome`` testenv attribute which can be set
  to True in which case it will produce a warning instead of an error on a failed testenv command outcome. Thanks
  Rebecka Gulliksson for the PR.

.. _release-2-2-0-packaging:

Packaging
---------

- fix `#280 <https://github.com/tox-dev/tox/issues/280>`_: properly skip missing interpreter if {envsitepackagesdir} is
  present in commands. Thanks BB:ceridwenv

.. _release-2-1-1:

********************
 2.1.1 (2015-06-23)
********************

.. _release-2-1-1-changes:

Changes
-------

- report skipped platforms as skips in the summary

.. _release-2-1-1-fixed:

Fixed
-----

- fix platform skipping for detox

.. _release-2-1-0:

********************
 2.1.0 (2015-06-19)
********************

.. _release-2-1-0-added:

Added
-----

- allow envlist to be a multi-line list, to intersperse comments and have long envlist settings split more naturally.
  Thanks Andre Caron.
- introduce a TOX_TESTENV_PASSENV setting which is honored when constructing the set of environment variables for test
  environments. Thanks Marc Abramowitz for pushing in this direction.

.. _release-2-1-0-changes:

Changes
-------

- remove experimental --set-home option which was hardly used and hackily implemented (if people want home-directory
  isolation we should figure out a better way to do it, possibly through a plugin)

.. _release-2-1-0-fixed:

Fixed
-----

- fix `#258 <https://github.com/tox-dev/tox/issues/258>`_, fix `#248 <https://github.com/tox-dev/tox/issues/248>`_, fix
  `#253 <https://github.com/tox-dev/tox/issues/253>`_: for non-test commands (installation, venv creation) we pass in
  the full invocation environment.
- fix `#259 <https://github.com/tox-dev/tox/issues/259>`_: passenv is now a line-list which allows interspersing
  comments. Thanks stefano-m.

.. _release-2-0-2:

********************
 2.0.2 (2015-06-03)
********************

.. _release-2-0-2-added:

Added
-----

- add SYSTEMDRIVE into default passenv on windows to allow pip6 to work. Thanks Michael Krause.

.. _release-2-0-2-fixed:

Fixed
-----

- fix `#247 <https://github.com/tox-dev/tox/issues/247>`_: tox now passes the LANG variable from the tox invocation
  environment to the test environment by default.

.. _release-2-0-1:

********************
 2.0.1 (2015-05-13)
********************

.. _release-2-0-1-packaging:

Packaging
---------

- fix wheel packaging to properly require argparse on py26.

.. _release-2-0-0:

********************
 2.0.0 (2015-05-12)
********************

.. _release-2-0-0-added:

Added
-----

- introduce experimental (not much documented yet) plugin system based on pytest's externalized "pluggy" system. See
  tox/hookspecs.py for the current hooks.
- introduce parser.add_testenv_attribute() to register an ini-variable for testenv sections. Can be used from plugins
  through the tox_add_option hook.

.. _release-2-0-0-changes:

Changes
-------

- (new) introduce environment variable isolation: tox now only passes the PATH and PIP_INDEX_URL variable from the tox
  invocation environment to the test environment and on Windows also ``SYSTEMROOT``, ``PATHEXT``, ``TEMP`` and ``TMP``
  whereas on unix additionally ``TMPDIR`` is passed. If you need to pass through further environment variables you can
  use the new ``passenv`` setting, a space-separated list of environment variable names. Each name can make use of
  fnmatch-style glob patterns. All environment variables which exist in the tox-invocation environment will be copied to
  the test environment.
- a new ``--help-ini`` option shows all possible testenv settings and their defaults.
- (new) introduce a way to specify on which platform a testenvironment is to execute: the new per-venv "platform"
  setting allows one to specify a regular expression which is matched against sys.platform. If platform is set and
  doesn't match the platform spec in the test environment the test environment is ignored, no setup or tests are
  attempted.
- show and store in json the version dependency information for each venv
- tox has now somewhat pep8 clean code, thanks to Volodymyr Vitvitski.
- rename internal files -- tox offers no external API except for the experimental plugin hooks, use tox internals at
  your own risk.

.. _release-2-0-0-fixed:

Fixed
-----

- (new) add per-venv "ignore_errors" setting, which defaults to False. If ``True``, a non-zero exit code from one
  command will be ignored and further commands will be executed (which was the default behavior in tox < 2.0). If
  ``False`` (the default), then a non-zero exit code from one command will abort execution of commands for that
  environment.
- fix `#120 <https://github.com/tox-dev/tox/issues/120>`_: allow substitution for the commands section. Thanks Volodymyr
  Vitvitski.
- fix `#235 <https://github.com/tox-dev/tox/issues/235>`_: fix AttributeError with --installpkg. Thanks Volodymyr
  Vitvitski.
- fix `#240 <https://github.com/tox-dev/tox/issues/240>`_: allow one to specify empty argument list without it being
  rewritten to ".". Thanks Daniel Hahler.

.. _release-2-0-0-deprecated:

Deprecated
----------

- remove the long-deprecated "distribute" option as it has no effect these days.
- DEPRECATE distshare in documentation

.. _release-2-0-0-packaging:

Packaging
---------

- fix `#233 <https://github.com/tox-dev/tox/issues/233>`_: avoid hanging with tox-setuptools integration example. Thanks
  simonb.

.. _release-1-9-2:

********************
 1.9.2 (2015-03-23)
********************

.. _release-1-9-2-changes:

Changes
-------

- backout ability that --force-dep substitutes name/versions in requirement files due to various issues. This fixes
  `#228 <https://github.com/tox-dev/tox/issues/228>`_, fixes `#230 <https://github.com/tox-dev/tox/issues/230>`_, fixes
  `#231 <https://github.com/tox-dev/tox/issues/231>`_ which popped up with 1.9.1.

.. _release-1-9-1:

********************
 1.9.1 (2015-03-23)
********************

.. _release-1-9-1-added:

Added
-----

- allow --force-dep to override dependencies in "-r" requirements files. Thanks Sontek for the PR.

.. _release-1-9-1-changes:

Changes
-------

- use a file instead of a pipe for command output in "--result-json". Fixes some termination issues with python2.6.

.. _release-1-9-1-fixed:

Fixed
-----

- fix `#227 <https://github.com/tox-dev/tox/issues/227>`_: use "-m virtualenv" instead of "-mvirtualenv" to make it work
  with pyrun. Thanks Marc-Andre Lemburg.

.. _release-1-9-0:

********************
 1.9.0 (2015-02-24)
********************

.. _release-1-9-0-changes:

Changes
-------

- refine determination if we run from Jenkins, thanks Borge Lanes.
- echo output to stdout when ``--report-json`` is used

.. _release-1-9-0-fixed:

Fixed
-----

- fix `#193 <https://github.com/tox-dev/tox/issues/193>`_: Remove ``--pre`` from the default ``install_command``; by
  default tox will now only install final releases from PyPI for unpinned dependencies. Use ``pip_pre = true`` in a
  testenv or the ``--pre`` command-line option to restore the previous behavior.
- fix `#199 <https://github.com/tox-dev/tox/issues/199>`_: fill resultlog structure ahead of virtualenv creation
- fix `#124 <https://github.com/tox-dev/tox/issues/124>`_: ignore command exit codes; when a command has a "-" prefix,
  tox will ignore the exit code of that command
- fix `#198 <https://github.com/tox-dev/tox/issues/198>`_: fix broken envlist settings, e.g. {py26,py27}{-lint,}
- fix `#191 <https://github.com/tox-dev/tox/issues/191>`_: lessen factor-use checks

.. _release-1-9-0-packaging:

Packaging
---------

- fix `#11 <https://github.com/tox-dev/tox/issues/11>`_: add a ``skip_install`` per-testenv setting which prevents the
  installation of a package. Thanks Julian Krause.

.. _release-1-8-1:

********************
 1.8.1 (2014-10-24)
********************

.. _release-1-8-1-added:

Added
-----

- allow escaping curly braces with "\". Thanks Marc Abramowitz for the PR.
- allow "." names in environment names such that "py27-django1.7" is a valid environment name. Thanks Alex Gaynor and
  Alex Schepanovski.

.. _release-1-8-1-changes:

Changes
-------

- report subprocess exit code when execution fails. Thanks Marius Gedminas.

.. _release-1-8-1-fixed:

Fixed
-----

- fix `#190 <https://github.com/tox-dev/tox/issues/190>`_: allow setenv to be empty.

.. _release-1-8-0:

********************
 1.8.0 (2014-09-24)
********************

.. _release-1-8-0-changes:

Changes
-------

- better report if we can't get version_info from an interpreter executable. Thanks Floris Bruynooghe.

.. _release-1-8-0-fixed:

Fixed
-----

- fix `#148 <https://github.com/tox-dev/tox/issues/148>`_: remove "__PYVENV_LAUNCHER__" from os.environ when starting
  subprocesses. Thanks Steven Myint.
- fix `#152 <https://github.com/tox-dev/tox/issues/152>`_: set VIRTUAL_ENV when running test commands, thanks Florian
  Ludwig.

.. _release-1-8-0-documentation:

Documentation
-------------

- new multi-dimensional configuration support. Many thanks to Alexander Schepanovski for the complete PR with docs. And
  to Mike Bayer and others for testing and feedback.

.. _release-1-7-2:

********************
 1.7.2 (2014-07-15)
********************

.. _release-1-7-2-added:

Added
-----

- support optional env variable substitution, thanks Morgan Fainberg for PR86.

.. _release-1-7-2-fixed:

Fixed
-----

- fix `#150 <https://github.com/tox-dev/tox/issues/150>`_: parse {posargs} more like we used to do it pre 1.7.0. The
  1.7.0 behavior broke a lot of OpenStack projects. See PR85 and the issue discussions for (far) more details, hopefully
  resulting in a more refined behavior in the 1.8 series. And thanks to Clark Boylan for the PR.
- fix `#59 <https://github.com/tox-dev/tox/issues/59>`_: add a config variable ``skip-missing-interpreters`` as well as
  command line option ``--skip-missing-interpreters`` which won't fail the build if Python interpreters listed in
  tox.ini are missing. Thanks Alexandre Conrad for PR104.
- fix `#164 <https://github.com/tox-dev/tox/issues/164>`_: better traceback info in case of failing test commands.
  Thanks Marc Abramowitz for PR92.
- limit python hashseed to 1024 on Windows to prevent possible memory errors. Thanks March Schlaich for the PR90.

.. _release-1-7-1:

********************
 1.7.1 (2014-03-28)
********************

.. _release-1-7-1-fixed:

Fixed
-----

- fix `#162 <https://github.com/tox-dev/tox/issues/162>`_: don't list python 2.5 as compatible/supported
- fix `#158 <https://github.com/tox-dev/tox/issues/158>`_ and fix `#155 <https://github.com/tox-dev/tox/issues/155>`_:
  windows/virtualenv properly works now: call virtualenv through "python -m virtualenv" with the same interpreter which
  invoked tox. Thanks Chris Withers, Ionel Maries Cristian.

.. _release-1-7-0:

********************
 1.7.0 (2014-01-29)
********************

.. _release-1-7-0-added:

Added
-----

- introduce --no-network to tox's own test suite to skip tests requiring networks

.. _release-1-7-0-changes:

Changes
-------

- don't lookup "pip-script" anymore but rather just "pip" on windows as this is a pip implementation detail and changed
  with pip-1.5. It might mean that tox-1.7 is not able to install a different pip version into a virtualenv anymore.
- merged PR125: tox now sets "PYTHONHASHSEED" to a random value and offers a "--hashseed" option to repeat a test run
  with a specific seed. You can also use --hashsheed=noset to instruct tox to leave the value alone. Thanks Chris
  Jerdonek for all the work behind this.
- rework and simplify "commands" parsing and in particular posargs substitutions to avoid various win32/posix related
  quoting issues.
- make sure that the --installpkg option trumps any usedevelop settings in tox.ini or

.. _release-1-7-0-fixed:

Fixed
-----

- fix `#132 <https://github.com/tox-dev/tox/issues/132>`_: removing zip_safe setting (so it defaults to false) to allow
  installation of tox via easy_install/eggs. Thanks Jenisys.
- fix `#126 <https://github.com/tox-dev/tox/issues/126>`_: depend on virtualenv>=1.11.2 so that we can rely (hopefully)
  on a pip version which supports --pre. (tox by default uses to --pre). also merged in PR84 so that we now call
  "virtualenv" directly instead of looking up interpreters. Thanks Ionel Maries Cristian. This also fixes `#140
  <https://github.com/tox-dev/tox/issues/140>`_.
- fix `#129 <https://github.com/tox-dev/tox/issues/129>`_: tox now uses Popen(..., universal_newlines=True) to force
  creation of unicode stdout/stderr streams. fixes a problem on specific platform configs when creating virtualenvs with
  Python3.3. Thanks Jorgen Schäfer or investigation and solution sketch.
- fix `#128 <https://github.com/tox-dev/tox/issues/128>`_: enable full substitution in install_command, thanks for the
  PR to Ronald Evers
- fix `#105 <https://github.com/tox-dev/tox/issues/105>`_ -- don't depend on an existing HOME directory from tox tests.

.. _release-1-7-0-packaging:

Packaging
---------

- drop Python2.5 compatibility because it became too hard due to the setuptools-2.0 dropping support. tox now has no
  support for creating python2.5 based environments anymore and all internal special-handling has been removed.
- merged PR81: new option --force-dep which allows one to override tox.ini specified dependencies in setuptools-style.
  For example "--force-dep 'django<1.6'" will make sure that any environment using "django" as a dependency will get the
  latest 1.5 release. Thanks Bruno Oliveria for the complete PR.
- fix `#130 <https://github.com/tox-dev/tox/issues/130>`_: you can now set install_command=easy_install {opts}
  {packages} and expect it to work for repeated tox runs (previously it only worked when always recreating). Thanks
  jenisys for precise reporting.
- introduce --sitepackages to force sitepackages=True in all environments.

.. _release-1-6-1:

********************
 1.6.1 (2013-09-04)
********************

.. _release-1-6-1-fixed:

Fixed
-----

- fix `#116 <https://github.com/tox-dev/tox/issues/116>`_: make 1.6 introduced behavior of changing to a per-env HOME
  directory during install activities dependent on "--set-home" for now. Should re-establish the old behavior when no
  option is given.
- fix `#118 <https://github.com/tox-dev/tox/issues/118>`_: correctly have two tests use realpath(). Thanks Barry Warsaw.
- fix test runs on environments without a home directory (in this case we use toxinidir as the homedir)
- fix `#102 <https://github.com/tox-dev/tox/issues/102>`_: change to {toxinidir} when installing dependencies. This
  allows one to use relative path like in "-rrequirements.txt".

.. _release-1-6-1-security:

Security
--------

- fix `#117 <https://github.com/tox-dev/tox/issues/117>`_: python2.5 fix: don't use ``--insecure`` option because its
  very existence depends on presence of "ssl". If you want to support python2.5/pip1.3.1 based test environments you
  need to install ssl and/or use PIP_INSECURE=1 through ``setenv``. section.

.. _release-1-6-1-packaging:

Packaging
---------

- fix `#119 <https://github.com/tox-dev/tox/issues/119>`_: {envsitepackagesdir} is now correctly computed and has a
  better test to prevent regression.

.. _release-1-6-0:

********************
 1.6.0 (2013-08-15)
********************

.. _release-1-6-0-added:

Added
-----

- add --result-json option to write out detailed per-venv information into a json report file to be used by upstream
  tools.

.. _release-1-6-0-changes:

Changes
-------

- remove toxbootstrap.py for now because it is broken.
- if a HOMEDIR cannot be determined, use the toxinidir.
- refactor interpreter information detection to live in new tox/interpreters.py file, tests in
  tests/test_interpreters.py.

.. _release-1-6-0-fixed:

Fixed
-----

- fix `#91 <https://github.com/tox-dev/tox/issues/91>`_: python2.5 support by vendoring the virtualenv-1.9.1 script and
  forcing pip<1.4. Also the default [py25] environment modifies the default installer_command (new config option) to use
  pip without the "--pre" option which was introduced with pip-1.4 and is now required if you want to install non-stable
  releases. (tox defaults to install with "--pre" everywhere).
- fix `#1 <https://github.com/tox-dev/tox/issues/1>`_: empty setup files are properly detected, thanks Anthon van der
  Neuth
- fix `#109 <https://github.com/tox-dev/tox/issues/109>`_ and fix `#111 <https://github.com/tox-dev/tox/issues/111>`_:
  multiple "-e" options are now combined (previously the last one would win). Thanks Anthon van der Neut.

.. _release-1-6-0-documentation:

Documentation
-------------

- fix `#35 <https://github.com/tox-dev/tox/issues/35>`_: add new EXPERIMENTAL "install_command" testenv-option to
  configure the installation command with options for dep/pkg install. Thanks Carl Meyer for the PR and docs.

.. _release-1-6-0-packaging:

Packaging
---------

- during installation of dependencies HOME is now set to a pseudo location ({envtmpdir}/pseudo-home). If an index url
  was specified a .pydistutils.cfg file will be written with an index_url setting so that packages defining
  ``setup_requires`` dependencies will not silently use your HOME-directory settings or PyPI.
- add new config options ``usedevelop`` and ``skipsdist`` as well as a command line option ``--develop`` to install the
  package-under-test in develop mode. thanks Monty Tailor for the PR.
- always unset PYTHONDONTWRITEBYTE because newer setuptools doesn't like it

.. _release-1-5-0:

********************
 1.5.0 (2013-06-22)
********************

.. _release-1-5-0-changes:

Changes
-------

- make sure test commands are searched first in the virtualenv
- re-fix `#2 <https://github.com/tox-dev/tox/issues/2>`_ - add whitelist_externals to be used in ``[testenv*]``
  sections, allowing to avoid warnings for commands such as ``make``, used from the commands value.
- show (test) command that is being executed, thanks Lukasz Balcerzak
- re-license tox to MIT license
- depend on virtualenv-1.9.1

.. _release-1-5-0-fixed:

Fixed
-----

- fix `#97 <https://github.com/tox-dev/tox/issues/97>`_ - allow substitutions to reference from other sections (thanks
  Krisztian Fekete)

.. _release-1-5-0-documentation:

Documentation
-------------

- rename README.txt to README.rst to make bitbucket happier

.. _release-1-5-0-packaging:

Packaging
---------

- fix `#104 <https://github.com/tox-dev/tox/issues/104>`_: use setuptools by default, instead of distribute, now that
  setuptools has distribute merged.
- fix `#92 <https://github.com/tox-dev/tox/issues/92>`_ - fix {envsitepackagesdir} to actually work again

.. _release-1-4-3:

********************
 1.4.3 (2013-02-28)
********************

.. _release-1-4-3-added:

Added
-----

- introduce -l|--listenv option to list configured environments (thanks Lukasz Balcerzak)

.. _release-1-4-3-changes:

Changes
-------

- use pip-script.py instead of pip.exe on win32 to avoid the lock exe file on execution issue (thanks Philip Thiem)
- issue `#70 <https://github.com/tox-dev/tox/issues/70>`_ remove PYTHONDONTWRITEBYTECODE workaround now that virtualenv
  behaves properly (thanks g2p)
- look for "tox.ini" files in parent dirs of current dir (closes `#34 <https://github.com/tox-dev/tox/issues/34>`_)
- the "py" environment now by default uses the current interpreter (sys.executable) make tox' own setup.py test execute
  tests with it (closes `#46 <https://github.com/tox-dev/tox/issues/46>`_)
- change tests to not rely on os.path.expanduser (closes `#60 <https://github.com/tox-dev/tox/issues/60>`_), also make
  mock session return args[1:] for more precise checking (closes `#61 <https://github.com/tox-dev/tox/issues/61>`_)
  thanks to Barry Warsaw for both.

.. _release-1-4-3-fixed:

Fixed
-----

- fix `#84 <https://github.com/tox-dev/tox/issues/84>`_ - pypy on windows creates a bin not a scripts venv directory
  (thanks Lukasz Balcerzak)
- fix `#48 <https://github.com/tox-dev/tox/issues/48>`_ - win32 detection of pypy and other interpreters that are on
  PATH (thanks Gustavo Picon)
- fix grouping of index servers, it is now done by name instead of indexserver url, allowing to use it to separate
  dependencies into groups even if using the same default indexserver.

.. _release-1-4-3-documentation:

Documentation
-------------

- fix downloadcache determination to work according to docs: Only make pip use a download cache if PIP_DOWNLOAD_CACHE or
  a downloadcache=PATH testenv setting is present. (The ENV setting takes precedence)
- merged tox-quickstart command, contributed by Marc Abramowitz, which generates a default tox.ini after asking a few
  questions

.. _release-1-4-3-packaging:

Packaging
---------

- experimentally introduce --installpkg=PATH option to install a package rather than create/install an sdist package.
  This will still require and use tox.ini and tests from the current working dir (and not from the remote package).
- substitute {envsitepackagesdir} with the package installation directory (closes `#72
  <https://github.com/tox-dev/tox/issues/72>`_) (thanks g2p)

.. _release-1-4-2:

********************
 1.4.2 (2012-07-20)
********************

.. _release-1-4-2-changes:

Changes
-------

- "python setup.py test" now runs tox tests via tox :) also added an example on how to do it for your project.

.. _release-1-4-2-fixed:

Fixed
-----

- fix some tests which fail if /tmp is a symlink to some other place

.. _release-1-4-1:

********************
 1.4.1 (2012-07-03)
********************

.. _release-1-4-1-fixed:

Fixed
-----

- fix `#41 <https://github.com/tox-dev/tox/issues/41>`_ better quoting on windows - you can now use "<" and ">" in deps
  specifications, thanks Chris Withers for reporting

.. _release-1-4:

******************
 1.4 (2012-06-13)
******************

.. _release-1-4-added:

Added
-----

- support value substitution from other sections with the {[section]key} syntax
- add python3.3 to the default env list, so early adopters can test

.. _release-1-4-changes:

Changes
-------

- tweak and improve reporting
- refactor reporting and virtualenv manipulation to be more accessible from 3rd party tools
- drop python2.4 support (you can still have your tests run on
- make the install step honor a testenv's setenv setting (thanks Ralf Schmitt) v1.2 2011-11-10
- remove the virtualenv.py that was distributed with tox and depend on >=virtualenv-1.6.4 (possible now since the latter
  fixes a few bugs that the inlining tried to work around)

.. _release-1-4-fixed:

Fixed
-----

- fix `#26 <https://github.com/tox-dev/tox/issues/26>`_ - no warnings on absolute or relative specified paths for
  commands
- fix `#33 <https://github.com/tox-dev/tox/issues/33>`_ - commentchars are ignored in key-value settings allowing for
  specifying commands like: python -c "import sys ; print sys" which would formerly raise irritating errors because the
  ";" was considered a comment
- fix `#29 <https://github.com/tox-dev/tox/issues/29>`_ - correctly point to pytest explanation for importing modules
  fully qualified
- fix: allow one to specify wildcard filesystem paths when specifying dependencies such that tox searches for the
  highest version
- fix `#10 <https://github.com/tox-dev/tox/issues/10>`_: work around UnicodeDecodeError when invoking pip (thanks Marc
  Abramowitz)
- fix a problem with parsing {posargs} in tox commands (spotted by goodwill)
- fix the warning check for commands to be installed in testenvironment (thanks Michael Foord for reporting)

.. _release-1-4-documentation:

Documentation
-------------

- fix the links/checkout howtos in the docs python-2.4, just tox itself requires 2.5 or higher. v1.3 2011-12-21

.. _release-1-4-packaging:

Packaging
---------

- fix `#32 <https://github.com/tox-dev/tox/issues/32>`_ - use --system-site-packages and don't pass --no-site-packages
- fix issue `#21 <https://github.com/tox-dev/tox/issues/21>`_: clear PIP_REQUIRES_VIRTUALENV which avoids pip installing
  to the wrong environment, thanks to bb's streeter

.. _release-1-3:

******************
 1.3 (2011-12-21)
******************

.. _release-1-3-changes:

Changes
-------

- make the install step honor a testenv's setenv setting (thanks Ralf Schmitt)

.. _release-1-3-fixed:

Fixed
-----

- fix: allow to specify wildcard filesystem paths when specifying dependencies such that tox searches for the highest
  version

.. _release-1-3-packaging:

Packaging
---------

- fix issue issue21: clear PIP_REQUIRES_VIRTUALENV which avoids pip installing to the wrong environment, thanks to bb's
  streeter

.. _release-1-2:

******************
 1.2 (2011-11-10)
******************

.. _release-1-2-changes:

Changes
-------

- remove the virtualenv.py that was distributed with tox and depend on >=virtualenv-1.6.4 (possible now since the latter
  fixes a few bugs that the inling tried to work around)

.. _release-1-2-fixed:

Fixed
-----

- fix issue10: work around UnicodeDecodeError when inokving pip (thanks Marc Abramowitz)
- fix a problem with parsing {posargs} in tox commands (spotted by goodwill)
- fix the warning check for commands to be installed in testevironment (thanks Michael Foord for reporting)

.. _release-1-1:

******************
 1.1 (2011-07-08)
******************

.. _release-1-1-changes:

Changes
-------

- inline virtualenv.py (1.6.1) script to avoid a number of issues, particularly failing to install python3 environments
  from a python2 virtualenv installation.

.. _release-1-1-fixed:

Fixed
-----

- fix `#5 <https://github.com/tox-dev/tox/issues/5>`_ - don't require argparse for python versions that have it
- fix `#6 <https://github.com/tox-dev/tox/issues/6>`_ - recreate virtualenv if installing dependencies failed
- fix `#3 <https://github.com/tox-dev/tox/issues/3>`_ - fix example on frontpage
- fix `#2 <https://github.com/tox-dev/tox/issues/2>`_ - warn if a test command does not come from the test environment

.. _release-1-1-documentation:

Documentation
-------------

- rework and enhance docs for display on readthedocs.org

.. _release-1-1-packaging:

Packaging
---------

- fixed/enhanced: except for initial install always call "-U --no-deps" for installing the sdist package to ensure that
  a package gets upgraded even if its version number did not change. (reported on TIP mailing list and IRC)

.. _release-1-0:

******************
 1.0 (2011-05-28)
******************

.. _release-1-0-added:

Added
-----

- added a CONTRIBUTORS file

.. _release-1-0-changes:

Changes
-------

- move repository and toxbootstrap links to https://bitbucket.org/hpk42/tox
- toxbootstrap.py (used by jenkins build agents) now follows the latest release of virtualenv
- change the positional argument specifier to use {posargs:} syntax and fix issues `#15
  <https://github.com/tox-dev/tox/issues/15>`_ and `#10 <https://github.com/tox-dev/tox/issues/10>`_ by refining the
  argument parsing method (Chris Rose)
- remove use of inipkg lazy importing logic - the namespace/imports are anyway very small with tox.
- show path of the underlying virtualenv invocation and bootstrap virtualenv.py into a working subdir

.. _release-1-0-fixed:

Fixed
-----

- fix `#7 <https://github.com/tox-dev/tox/issues/7>`_: introduce a "minversion" directive such that tox bails out if it
  does not have the correct version.
- fix `#24 <https://github.com/tox-dev/tox/issues/24>`_: introduce a way to set environment variables for for test
  commands (thanks Chris Rose)
- fix `#22 <https://github.com/tox-dev/tox/issues/22>`_: require virtualenv-1.6.1, obsoleting virtualenv5 (thanks Jannis
  Leidel) and making things work with pypy-1.5 and python3 more seamlessly
- fix `#20 <https://github.com/tox-dev/tox/issues/20>`_: document format of URLs for specifying dependencies
- fix `#19 <https://github.com/tox-dev/tox/issues/19>`_: substitute Hudson for Jenkins everywhere following the renaming
  of the project. NOTE: if you used the special [tox:hudson] section it will now need to be named [tox:jenkins].
- fix issue 23 / apply some ReST fixes
- fix a fspath related assertion to work with debian installs which uses symlinks

.. _release-0-9:

******************
 0.9 (2010-11-25)
******************

.. _release-0-9-added:

Added
-----

- added support for working with different and multiple PyPI indexservers.
- new option: -r|--recreate to force recreation of virtualenv

.. _release-0-9-changes:

Changes
-------

- `#1 <https://github.com/tox-dev/tox/issues/1>`_: Add a toxbootstrap.py script for tox, thanks to Sridhar Ratnakumar
- depend on py>=1.4.0 which does not contain or install the py.test anymore which is now a separate distribution
  "pytest".

.. _release-0-9-fixed:

Fixed
-----

- fix pip-installation mixups by always unsetting PIP_RESPECT_VIRTUALENV (thanks Armin Ronacher)
- show logfile content if there is an error (makes CI output more readable)

.. _release-0-8:

******************
 0.8 (2010-07-30)
******************

.. _release-0-8-changes:

Changes
-------

- run pip/easy installs from the environment log directory, avoids naming clashes between env names and dependencies
  (thanks ronny)
- require a more recent version of py lib
- refactor and refine config detection to work from a single file and to detect the case where a python installation
  overwrote an old one and resulted in a new executable. This invalidates the existing virtualenvironment now.
- change all internal source to strip trailing whitespaces

.. _release-0-8-fixed:

Fixed
-----

- work around a virtualenv limitation which crashes if PYTHONDONTWRITEBYTECODE is set.

.. _release-0-6:

******************
 0.6 (2010-07-12)
******************

.. _release-0-6-fixed:

Fixed
-----

- fix OSX related bugs that could cause the caller's environment to get screwed (sorry). tox was using the same file as
  virtualenv for tracking the Python executable dependency and there also was confusion wrt links. this should be fixed
  now.
- fix long description, thanks Michael Foord

.. _release-0-5:

******************
 0.5 (2010-07-12)
******************

.. _release-0-5-changes:

Changes
-------

- initial release
