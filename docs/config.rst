.. _configuration:

Configuration
+++++++++++++

tox configuration can be split into two categories: core and environment specific. Core settings are options that can
be set once and used for all tox environments, while environment options are applied to the given tox environment only.

Discovery and file types
------------------------

With regards to the configuration format, at the moment we support the following formats:

- `INI <https://en.wikipedia.org/wiki/INI_file>`_.
- `TOML <https://toml.io/en/v1.0.0>`_.

Out of box tox supports five configuration locations prioritized in the following order:

1. ``tox.ini`` (INI),
2. ``setup.cfg`` (INI),
3. ``pyproject.toml`` with the ``tool.tox`` table, having ``legacy_tox_ini`` key (containing INI),
4. Native ``pyproject.toml`` under the ``tool.tox`` table (TOML),
5. ``tox.toml`` (TOML).

Historically, the INI format was created first, and TOML was added in 2024. The TOML format generally is more robust,
however is less powerful and more verbose. You should use TOML unless you need some of the more advanced features
that TOML does not support (such as conditional factors, generative environments to name a few -- however, PRs to
add support for these in TOML is welcome).

.. _tox-ini:

``tox.ini``
~~~~~~~~~~~

This configuration file uses:

- ``tox`` section to host core configuration,
- ``testenv:{env_name}`` section to host environment configuration,
- ``testenv`` section as base configuration for run environments (fallback location for missing values for a test/run
  environment),
- ``pkgenv`` section as base configuration for package environments (fallback location for missing values for a package
  environment).

For example:

.. code-block:: ini

    [tox]
    min_version = 4.20
    env_list =
        3.13
        3.12
        type

    [testenv]
    deps = pytest
    commands = pytest tests

    [testenv:type]
    deps = mypy
    commands = mypy src

``setup.cfg``
~~~~~~~~~~~~~
This configuration file uses:

- ``tox:tox`` section to host core configuration,
- ``testenv:{env_name}`` section to host environment configuration,
- ``testenv`` section as base configuration for run environments (fallback location for missing values for a test/run
  environment),
- ``pkgenv`` section as base configuration for package environments (fallback location for missing values for a package
  environment).

.. code-block:: ini

    [tox:tox]
    min_version = 4.0
    env_list =
        3.13
        3.12
        type

    [testenv]
    deps = pytest
    commands = pytest tests

    [testenv:type]
    deps = mypy
    commands = mypy src

``pyproject.toml`` - INI
~~~~~~~~~~~~~~~~~~~~~~~~
This configuration file is equivalent to :ref:`tox.ini <tox-ini>` format, with the difference that the text is stored
instead inside the ``pyproject.toml`` file under the ``tool.tox`` table and ``legacy_tox_ini`` key:

.. code-block:: toml

    [tool.tox]
    legacy_tox_ini = """
        [tox]
        min_version = 4.0
        env_list =
            py310
            py39
            type

        [testenv]
        deps = pytest
        commands = pytest tests

        [testenv:type]
        deps = mypy
        commands = mypy src
    """


.. _pyproject-toml-native:

``pyproject.toml`` - native
~~~~~~~~~~~~~~~~~~~~~~~~~~~

We support native TOML configuration via the ``pyproject.toml`` files ``tool.tox`` table. This configuration file uses:

- ``tool.tox`` table to host core configuration,
- ``tool.tox.env.{env_name}`` table to host environment configuration,
- ``tool.tox.env_run_base`` table as base configuration for run environments (fallback location for missing values for
  a test/run environment),
- ``tool.tox.env_pkg_base`` table as base configuration for package environments (fallback location for missing values
  for a package environment).

.. code-block:: toml

    [tool.tox]
    requires = ["tox>=4.19"]
    env_list = ["3.13", "3.12", "type"]

    [tool.tox.env_run_base]
    description = "Run test under {base_python}"
    commands = [["pytest"]]

    [tool.tox.env.type]
    description = "run type check on code base"
    deps = ["mypy==1.11.2", "types-cachetools>=5.5.0.20240820", "types-chardet>=5.0.4.6"]
    commands = [["mypy", "src{/}tox"], ["mypy", "tests"]]

``tox.toml``
~~~~~~~~~~~~

This configuration file is equivalent to :ref:`pyproject.toml - native <pyproject-toml-native>` with the difference
that it lives in a separate dedicated files and accordingly the ``tool.tox`` sub-table is no longer required.

For example:

.. code-block:: toml

    requires = ["tox>=4.19"]
    env_list = ["3.13", "3.12", "type"]

    [env_run_base]
    description = "Run test under {base_python}"
    commands = [["pytest"]]

    [env.type]
    description = "run type check on code base"
    deps = ["mypy==1.11.2", "types-cachetools>=5.5.0.20240820", "types-chardet>=5.0.4.6"]
    commands = [["mypy", "src{/}tox"], ["mypy", "tests"]]

.. _conf-core:

Core
----

The following options are set in the ``[tox]`` section of ``tox.ini`` or the ``[tox:tox]`` section of ``setup.cfg``.

.. conf::
   :keys: requires
   :default: <empty list>
   :version_added: 3.2.0

   Specify a list of :pep:`508` compliant dependencies that must be satisfied in the Python environment hosting tox when
   running the tox command. If any of these dependencies are not satisfied will automatically create a provisioned tox
   environment that does not have this issue, and run the tox command within that environment. See
   :ref:`provision_tox_env` for more details.

    .. tab:: TOML

       .. code-block:: toml

          [tool.tox]
          requires = [
            "tox>=4",
            "virtualenv>20.2",
          ]

    .. tab:: INI

       .. code-block:: ini

        [tox]
        requires =
            tox>=4
            virtualenv>20.2
.. conf::
   :keys: min_version, minversion
   :default: <current version of tox>

   A string to define the minimal tox version required to run. If the host's tox version is less than this, it will
   automatically create a provisioned tox environment that satisfies this requirement. See :ref:`provision_tox_env`
   for more details.

.. conf::
   :keys: provision_tox_env
   :default: .tox
   :version_added: 3.8.0

   Name of the tox environment used to provision a valid tox run environment.

   .. versionchanged:: 3.23.0

      When tox is invoked with the ``--no-provision`` flag, the provision won't be attempted,  tox will fail instead.

.. conf::
   :keys: env_list, envlist
   :default: <empty list>

   A list of environments to run by default (when the user does not specify anything during the invocation).

   .. versionchanged:: 3.4.0

      Which tox environments are run during the tox invocation can be further filtered via the operating system
      environment variable ``TOX_SKIP_ENV`` regular expression (e.g. ``py27.*`` means **don't** evaluate environments
      that start with the key ``py27``). Skipped environments will be logged at level two verbosity level.

.. conf::
   :keys: skip_missing_interpreters
   :default: config
   :version_added: 1.7.2

   Setting this to ``true`` will force ``tox`` to return success even if some of the specified environments were
   missing. This is useful for some CI systems or when running on a developer box, where you might only have a subset
   of all your supported interpreters installed but don't want to mark the build as failed because of it. As expected,
   the command line switch always overrides this setting if passed on the invocation. Setting it to ``config`` means
   that the value is read from the config file.

.. conf::
   :keys: tox_root, toxinidir

   The root directory for the tox project (where the configuration file is found).

.. conf::
   :keys: work_dir, toxworkdir
   :default: {tox_root}/.tox

   Directory for tox to generate its environments into, will be created if it does not exist.

.. conf::
   :keys: temp_dir
   :default: {work_dir}/.tmp

   Directory where to put tox temporary files. For example: we create a hard link (if possible, otherwise new copy) in
   this directory for the project package. This ensures tox works correctly when having parallel runs (as each session
   will have its own copy of the project package - e.g. the source distribution).

.. conf::
   :keys: no_package, skipsdist
   :default: false

   Flag indicating to perform the packaging operation or not. Set it to ``true`` when using tox for an application,
   instead of a library.

.. conf::
   :keys: package_env, isolated_build_env
   :default: .pkg
   :version_added: 3.3.0

    Default name of the virtual environment used to create a source distribution from the source tree.

.. conf::
   :keys: package_root, setupdir
   :default: {tox_root}

    Indicates where the packaging root file exists (historically setup.py file or pyproject.toml now).

.. conf::
   :keys: labels
   :default: <empty dictionary>

   A mapping of label names to environments it applies too. For example:

    .. tab:: TOML

       .. code-block:: toml

          [tool.tox]
          labels = { test = ["3.13", "3.12"], static = ["ruff", "mypy"] }

    .. tab:: INI

       .. code-block:: ini

          [tox]
          labels =
               test = 3.13, 3.12
               static = ruff, mypy

.. conf::
   :keys: on_platform
   :constant:

   A constant holding the platform of the tox runtime environment.

Python language core options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. conf::
   :keys: ignore_base_python_conflict, ignore_basepython_conflict
   :default: True

    .. versionadded:: 3.1.0

    tox allows setting the Python version for an environment via the :ref:`base_python` setting. If that's not set tox
    can set a default value from the environment name (e.g. ``py310`` implies Python 3.10). Matching up the Python
    version with the environment name has became expected at this point, leading to surprises when some configs don't
    do so. To help with sanity of users, an error will be raised whenever the environment name version does not match
    up with this expectation.

    Furthermore, we allow hard enforcing this rule by setting this flag to ``true``. In such cases we ignore the
    :ref:`base_python` and instead always use the base Python implied from the Python name. This allows you to configure
    :ref:`base_python` in the :ref:`base` section without affecting environments that have implied base Python versions.

.. _conf-testenv:

tox environment
---------------

These are configuration for the tox environments (either packaging or run type).

Base options
~~~~~~~~~~~~

.. conf::
   :keys: envname, env_name
   :constant:

   The name of the tox environment.

.. conf::
   :keys: env_dir, envdir
   :default: {work_dir}/{env_name}
   :version_added: 1.5

   Directory assigned to the tox environment. If not absolute it would be treated as relative to :ref:`tox_root`.

.. conf::
   :keys: env_tmp_dir, envtmpdir
   :default: {work_dir}/{env_name}/tmp

   A folder that is always reset at the start of the run.

.. conf::
   :keys: env_log_dir, envlogdir
   :default: {work_dir}/{env_name}/log

   A folder containing log files about tox runs. It's always reset at the start of the run. Currently contains every
   process invocation in the format of ``<index>-<run name>.log``, and details the execution request (command,
   environment variables, current working directory, etc.) and its outcome (exit code and standard output/error
   content).

.. conf::
   :keys: platform

   Run on platforms that match this regular expression (empty means any platform). If a non-empty expression is defined
   and does not match against the ``sys.platform`` string the entire test environment will be skipped and none of the
   commands will be executed. Running ``tox -e <platform_name>`` will run commands for a particular platform and skip
   the rest.

.. conf::
   :keys: pass_env, passenv
   :default: <empty list>

   Environment variables to pass on to the tox environment. The values are evaluated as UNIX shell-style wildcards, see
   `fnmatch <https://docs.python.org/3/library/fnmatch.html>`_  If a specified environment variable doesn't exist in the
   tox invocation environment it is ignored. The list of environment variable names is not case sensitive, for example:
   passing ``A`` or ``a`` will pass through both ``A`` and ``a``.

   Some variables are always passed through to ensure the basic functionality of standard library functions or tooling like
   pip. This is also not case sensitive on all platforms except Windows.

    .. list-table:: Environment Variables per Operating System
        :widths: 25 25 25 25
        :header-rows: 1

        *   - Environment Variable
            - Linux
            - MacOS
            - Windows
        *   - https_proxy
            - ✅
            - ✅
            - ✅
        *   - http_proxy
            - ✅
            - ✅
            - ✅
        *   - no_proxy
            - ✅
            - ✅
            - ✅
        *   - LANG
            - ✅
            - ✅
            - ✅
        *   - LANGUAGE
            - ✅
            - ✅
            - ✅
        *   - CURL_CA_BUNDLE
            - ✅
            - ✅
            - ✅
        *   - SSL_CERT_FILE
            - ✅
            - ✅
            - ✅
        *   - CC
            - ✅
            - ✅
            - ✅
        *   - CFLAGS
            - ✅
            - ✅
            - ✅
        *   - CCSHARED
            - ✅
            - ✅
            - ✅
        *   - CXX
            - ✅
            - ✅
            - ✅
        *   - CPPFLAGS
            - ✅
            - ✅
            - ✅
        *   - LD_LIBRARY_PATH
            - ✅
            - ✅
            - ✅
        *   - LDFLAGS
            - ✅
            - ✅
            - ✅
        *   - HOME
            - ✅
            - ✅
            - ✅
        *   - FORCE_COLOR
            - ✅
            - ✅
            - ✅
        *   - NO_COLOR
            - ✅
            - ✅
            - ✅
        *   - TMPDIR
            - ✅
            - ✅
            - ❌
        *   - TEMP
            - ❌
            - ❌
            - ✅
        *   - TMP
            - ❌
            - ❌
            - ✅
        *   - USERPROFILE
            - ❌
            - ❌
            - ✅
        *   - PATHEXT
            - ❌
            - ❌
            - ✅
        *   - MSYSTEM
            - ❌
            - ❌
            - ✅
        *   - WINDIR
            - ❌
            - ❌
            - ✅
        *   - APPDATA
            - ❌
            - ❌
            - ✅
        *   - PROGRAMDATA
            - ❌
            - ❌
            - ✅
        *   - PROGRAMFILES(x86)
            - ❌
            - ❌
            - ✅
        *   - SYSTEMDRIVE
            - ❌
            - ❌
            - ✅
        *   - SYSTEMROOT
            - ❌
            - ❌
            - ✅
        *   - COMSPEC
            - ❌
            - ❌
            - ✅
        *   - PROCESSOR_ARCHITECTURE
            - ❌
            - ❌
            - ✅
        *   - NUMBER_OF_PROCESSORS
            - ❌
            - ❌
            - ✅
        *   - PIP_*
            - ✅
            - ✅
            - ✅
        *   - VIRTUALENV_*
            - ✅
            - ✅
            - ✅
        *   - NETRC
            - ✅
            - ✅
            - ✅
        *   - NIX_LD*
            - ✅
            - ✅
            - ❌
        *   - NIX_LD_LIBRARY_PATH
            - ✅
            - ✅
            - ❌



   More environment variable-related information
   can be found in :ref:`environment variable substitutions`.

.. conf::
   :keys: set_env, setenv

   A dictionary of environment variables to set when running commands in the tox environment.

   In addition, there is an option to include an existing environment file. See the different syntax for TOML and INI below.

    .. tab:: TOML

       .. code-block:: toml

          [tool.tox.env_run_base]
          set_env = { file = "conf{/}local.env", TEST_TIMEOUT = 30 }

    .. tab:: INI

       .. code-block:: ini

          [testenv]
          set_env = file|conf{/}local.env
               TEST_TIMEOUT = 30


    The env file path may include previously defined tox variables:


    .. tab:: TOML

       .. code-block:: toml

          [tool.tox.env_run_base]
          set_env = { file = "{env:variable}" }

    .. tab:: INI

       .. code-block:: ini

          [testenv]
          set_env = file|{env:variable}


    .. note::

       Environment files are processed using the following rules:

       - blank lines are ignored,
       - lines starting with the ``#`` character are ignored,
       - each line is in KEY=VALUE format; both the key and the value are stripped,
       - there is no special handling of quotation marks, they are part of the key or value.

   More environment variable-related information
   can be found in :ref:`environment variable substitutions`.

.. conf::
   :keys: parallel_show_output
   :default: False
   :version_added: 3.7

   If set to ``True`` the content of the output will always be shown  when running in parallel mode.

.. conf::
   :keys: recreate
   :default: False

   Always recreate virtual environment if this option is true, otherwise leave it up to tox.

.. conf::
   :keys: allowlist_externals
   :default: <empty list>

   Each line specifies a command name (in glob-style pattern format) which can be used in the commands section even if
   it's located outside of the tox environment. For example: if you use the unix *rm* command for running tests you can
   list ``allowlist_externals=rm`` or ``allowlist_externals=/usr/bin/rm``. If you want to allow all external
   commands you can use ``allowlist_externals=*`` which will match all commands (not recommended).

.. conf::
   :keys: labels
   :default: <empty list>
   :ref_suffix: env

   A list of labels to apply for this environment. For example:

    .. tab:: TOML

       .. code-block:: toml

          [tool.tox.env_run_base]
          labels = ["test", "core"]
          [tool.tox.env.flake8]
          labels = ["mypy"]

    .. tab:: INI

       .. code-block:: ini

          [testenv]
          labels = test, core
          [testenv:flake8]
          labels = mypy

Execute
~~~~~~~

.. conf::
   :keys: suicide_timeout
   :default: 0.0
   :version_added: 3.15.2

    When an interrupt is sent via Ctrl+C or the tox process is killed with a SIGTERM, a SIGINT is sent to all foreground
    processes. The :ref:`suicide_timeout` gives the running process time to cleanup and exit before receiving (in some
    cases, a duplicate) SIGINT from tox.

.. conf::
   :keys: interrupt_timeout
   :default: 0.3
   :version_added: 3.15

    When tox is interrupted, it propagates the signal to the child process after :ref:`suicide_timeout` seconds. If the
    process still hasn't exited after :ref:`interrupt_timeout` seconds, its sends a SIGTERM.

.. conf::
   :keys: terminate_timeout
   :default: 0.2
   :version_added: 3.15

    When tox is interrupted, after waiting :ref:`interrupt_timeout` seconds, it propagates the signal to the child
    process, waits :ref:`interrupt_timeout` seconds, sends it a SIGTERM, waits :ref:`terminate_timeout` seconds, and
    sends it a SIGKILL if it hasn't exited.

Run
~~~

.. conf::
   :keys: base
   :default: testenv
   :version_added: 4.0.0

   Inherit missing keys from these sections.

.. conf::
   :keys: runner
   :default:
   :version_added: 4.0.0

   The tox execute used to evaluate this environment. Defaults to Python virtual environments, however may be
   overwritten by plugins.

.. conf::
   :keys: description
   :default: <empty string>

   A short description of the environment, this will be used to explain the environment to the user upon listing
   environments.

.. conf::
   :keys: depends
   :default: <empty list>

   tox environments that this environment depends on (must be run after those).

   .. warning::

      ``depends`` does not pull in dependencies into the run target, for example if you select ``py310,py39,coverage``
      via the ``-e`` tox will only run those three (even if ``coverage`` may specify as ``depends`` other targets too -
      such as ``py310, py39, py38``). This is solely meant to specify dependencies and order in between a target run
      set.

.. conf::
   :keys: commands_pre
   :default: <empty list>
   :version_added: 3.4

   Commands to run before running the :ref:`commands`. All evaluation and configuration logic applies from
   :ref:`commands`.

.. conf::
   :keys: commands
   :default: <empty list>

   The commands to be called for testing. Only execute if :ref:`commands_pre` succeed. Each line is interpreted as one
   command; however a command can be split over multiple lines by ending the line with the ``\`` character.

   Commands will execute one by one in sequential fashion until one of them fails (their exit code is non-zero) or all
   of them succeed. The exit code of a command may be ignored (meaning they are always considered successful) by
   prefixing the command with a dash (``-``) - this is similar to how ``make`` recipe lines work. The outcome of the
   environment is considered successful only if all commands (these + setup + teardown) succeeded (exit code ignored
   via the ``-`` or success exit code value of zero).

   .. note::

      The virtual environment binary path (see :ref:`env_bin_dir`) is prepended to the ``PATH`` environment variable,
      meaning commands will first try to resolve to an executable from within the virtual environment, and only after
      that outside of it. Therefore ``python`` translates as the virtual environments ``python`` (having the same
      runtime version as the :ref:`base_python`), and ``pip`` translates as the virtual environments ``pip``.

   .. note::

       ``shlex`` POSIX-mode quoting rules are used to split the command line into arguments on all
       supported platforms as of tox 4.4.0.

       The backslash ``\`` character can be used to escape quotes, whitespace, itself, and
       other characters (except on Windows, where a backslash in a path will not be interpreted as an escape).
       Unescaped single quote will disable the backslash escape until closed by another unescaped single quote.
       For more details, please see :doc:`shlex parsing rules <python:library/shlex>`.

   .. note::

     Inline scripts can be used, however note these are discovered from the project root directory, and is not
     influenced by :ref:`change_dir` (this only affects the runtime current working directory). To make this behavior
     explicit we recommend that you make inline scripts absolute paths by prepending ``{tox_root}``, instead of
     ``path/to/my_script`` prefer ``{tox_root}{/}path{/}to{/}my_script``. If your inline script is platform dependent
     refer to :ref:`platform-specification` on how to select different script per platform.

.. conf::
   :keys: commands_post
   :default: <empty list>

   Commands to run after running the :ref:`commands`. Execute regardless of the outcome of both :ref:`commands` and
   :ref:`commands_pre`. All evaluation and configuration logic applies from :ref:`commands`.

.. conf::
   :keys: change_dir, changedir
   :default: {tox_root}

   Change to this working directory when executing the test command. If the directory does not exist yet, it will be
   created (required for Windows to be able to execute any command).

.. conf::
   :keys: args_are_paths
   :default: False

   Treat positional arguments passed to tox as file system paths and - if they exist on the filesystem and are in
   relative format - rewrite them according to the current and :ref:`change_dir` working directory. This handles
   automatically transforming relative paths specified on the CLI to relative paths respective of the commands executing
   directory.

.. conf::
   :keys: ignore_errors
   :default: False

   When executing the commands keep going even if a sub-command exits with non-zero exit code. The overall status will
   be "commands failed", i.e. tox will exit non-zero in case any command failed. It may be helpful to note that this
   setting is analogous to the ``-k`` or ``--keep-going`` option of GNU Make.

.. conf::
   :keys: ignore_outcome
   :default: False

   If set to true a failing result of this test environment will not make tox fail (instead just warn).

.. conf::
   :keys: skip_install
   :default: False
   :version_added: 1.9

   Skip installation of the package.  This can be used when you need the virtualenv management but do not want to
   install the current package into that environment.

.. conf::
   :keys: package_env
   :default: {package_env}
   :version_added: 4.0.0
   :ref_suffix: env

   Name of the virtual environment used to create a source distribution from the source tree for this environment.

.. conf::
   :keys: package_tox_env_type
   :version_added: 4.0.0
   :default: virtualenv-pep-517

   tox package type used to package.

.. _python-options:

Python options
~~~~~~~~~~~~~~
.. conf::
   :keys: base_python, basepython
   :default: <{env_name} python factor> or <python version of tox>

   Name or path to a Python interpreter which will be used for creating the virtual environment, first one found wins.
   This determines in practice the Python for what we'll create a virtual isolated environment. Use this to specify the
   Python version for a tox environment. If not specified, the virtual environments factors (e.g. name part) will be
   used to automatically set one. For example, ``py310`` means ``python3.10``, ``py3`` means ``python3`` and ``py``
   means ``python``. If the name does not match this pattern the same Python version tox is installed into will be used.

    .. versionchanged:: 3.1

        After resolving this value if the interpreter reports back a different version number than implied from the name
        a warning will be printed by default. However, if :ref:`ignore_basepython_conflict` is set, the value is
        ignored and we force the :ref:`base_python` implied from the factor name.

    .. note::

      Leaving this unset will cause an error if the package under test has a different Python requires than tox itself
      and tox is installed into a Python that's not supported by the package. For example, if your package requires
      Python 3.10 or later, and you install tox in Python 3.9, when you run a tox environment that has left this
      unspecified tox will use Python 3.9 to build and install your package which will fail given it requires 3.10.

.. conf::
   :keys: env_site_packages_dir, envsitepackagesdir
   :constant:

   The Python environments site package - where packages are installed (the purelib folder path).

.. conf::
   :keys: env_bin_dir, envbindir
   :constant:

   The binary folder where console/gui scripts are generated during installation.

.. conf::
   :keys: env_python, envpython
   :constant:

   The Python executable from within the tox environment.

Python run
~~~~~~~~~~
.. conf::
   :keys: dependency_groups
   :default: <empty list>
   :version_added: 4.22

   A list of names of dependency groups (as defined by :pep:`735`) to install into this Python environment. The
   installation will happen before installing the package or any of its dependencies.

   For example:

    .. tab:: TOML

       .. code-block:: toml

          [dependency-groups]
          test = [
             "pytest>=8",
          ]

          [tool.tox.env_run_base]
          dependency_groups = [
            "test",
          ]

    .. tab:: INI

       .. code-block:: ini

        [testenv]
        dependency_groups =
            test

       .. code-block:: toml

          [dependency-groups]
          test = [
             "pytest>=8",
          ]

.. conf::
   :keys: deps
   :default: <empty list>

   Name of the Python dependencies. Installed into the environment prior to project after environment creation, but
   before package installation. All installer commands are executed using the :ref:`tox_root` as the current working
   directory. Each value must be one of:

   - a Python dependency as specified by :pep:`440`,
   - a `requirement file <https://pip.pypa.io/en/stable/user_guide/#requirements-files>`_ when the value starts with
     ``-r`` (followed by a file path),
   - a `constraint file <https://pip.pypa.io/en/stable/user_guide/#constraints-files>`_ when the value starts with
     ``-c`` (followed by a file path).

   If you are only defining :pep:`508` requirements (aka no pip requirement files), you should use
   :ref:`dependency_groups` instead.

   For example:
    .. tab:: TOML

       .. code-block:: toml

          [tool.tox.env_run_base]
          deps = [
            "pytest>=8",
            "-r requirements.txt",
            "-c constraints.txt",
          ]

    .. tab:: INI

       .. code-block:: ini

        [testenv]
        deps =
            pytest>=7,<8
            -r requirements.txt
            -c constraints.txt

.. conf::
   :keys: use_develop, usedevelop
   :default: false
   :version_added: 1.6

   Install the current package in development mode using :pep:`660`. This means that the package will
   be installed in-place and editable.

   .. note::

      ``package = editable`` is the preferred way to enable development/editable mode. See the details in :ref:`package`.

   .. note::

      PEP-660 introduced a standardized way of installing a package in development mode, providing the same effect as if
      ``pip install -e`` was used.

.. conf::
   :keys: package
   :version_added: 4.0

   When option can be one of ``wheel``, ``sdist``, ``editable``, ``editable-legacy``, ``skip``, or ``external``. If
   :ref:`use_develop` is set this becomes a constant of ``editable``. If :ref:`skip_install` is set this becomes a
   constant of ``skip``.


.. conf::
   :keys: wheel_build_env
   :version_added: 4.0
   :default: <package_env>-<python-flavor-lowercase><python-version-no-dot>

   If :ref:`package` is set to ``wheel`` this will be the tox Python environment in which the wheel will be
   built. The value is generated to be unique per Python flavor and version, and prefixed with :ref:`package_env` value.
   This is to ensure the target interpreter and the generated wheel will be compatible. If you have a wheel that can be
   reused across multiple Python versions set this value to the same across them (to avoid building a new wheel for
   each one of them).

.. conf::
   :keys: extras
   :version_added: 2.4
   :default: <empty list>

   A list of "extras" from the package to be installed. For example, ``extras = testing`` is equivalent to ``[testing]``
   in a ``pip install`` command.

.. _external-package-builder:

External package builder
~~~~~~~~~~~~~~~~~~~~~~~~

tox supports operating with externally built packages. External packages might be provided in two ways:

- explicitly via the :ref:`--installpkg <tox-run---installpkg>` CLI argument,
- setting the :ref:`package` to ``external`` and using a tox packaging environment named ``<package_env>_external``
  (see :ref:`package_env`) to build the package. The tox packaging environment takes all configuration flags of a
  :ref:`python environment <python-options>`, plus the following:

.. conf::
   :keys: deps
   :default: <empty list>
   :ref_suffix: external

   Name of the Python dependencies as specified by :pep:`440`. Installed into the environment prior running the build
   commands. All installer commands are executed using the :ref:`tox_root` as the current working directory.

.. conf::
   :keys: commands
   :default: <empty list>
   :ref_suffix: external

   Commands to run that will build the package. If any command fails the packaging operation is considered failed and
   will fail all environments using that package.

.. conf::
   :keys: ignore_errors
   :default: False
   :ref_suffix: external

   When executing the commands keep going even if a sub-command exits with non-zero exit code. The overall status will
   be "commands failed", i.e. tox will exit non-zero in case any command failed. It may be helpful to note that this
   setting is analogous to the ``-k`` or ``--keep-going`` option of GNU Make.

.. conf::
   :keys: change_dir, changedir
   :default: {tox_root}
   :ref_suffix: external

   Change to this working directory when executing the package build command. If the directory does not exist yet, it
   will be created (required for Windows to be able to execute any command).

.. conf::
   :keys: package_glob
   :default: {envtmpdir}{/}dist{/}*

   A glob that should match the wheel/sdist file to install. If no file or multiple files is matched the packaging
   operation is considered failed and will raise an error.


Python virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. conf::
   :keys: system_site_packages, sitepackages
   :default: False

   Create virtual environments that also have access to globally installed packages. Note the default value may be
   overwritten by the ``VIRTUALENV_SYSTEM_SITE_PACKAGES`` environment variable.

   .. warning::

     In cases where a command line tool is also installed globally you have to make sure that you use the tool installed
     in the virtualenv by using ``python -m <command line tool>`` (if supported by the tool) or
     ``{env_bin_dir}/<command line tool>``. If you forget to do that you will get an error.

.. conf::
   :keys: always_copy, alwayscopy
   :default: False

   Force virtualenv to always copy rather than symlink. Note the default value may be overwritten by the
   ``VIRTUALENV_COPIES`` or ``VIRTUALENV_ALWAYS_COPY`` (in that order) environment variables.  This is useful for
   situations where hardlinks don't work (e.g. running in VMS with Windows guests).

.. conf::
   :keys: download
   :version_added: 3.10
   :default: False

   True if you want virtualenv to upgrade pip/wheel/setuptools to the latest version. Note the default value may be
   overwritten by the ``VIRTUALENV_DOWNLOAD`` environment variable. If (and only if) you want to choose a specific
   version (not necessarily the latest) then you can add ``VIRTUALENV_PIP=20.3.3`` (and similar) to your :ref:`set_env`.


Python virtual environment packaging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. conf::
   :keys: meta_dir
   :version_added: 4.0.0
   :default: {env_dir}/.meta

   Directory where to put the project metadata files.

.. conf::
   :keys: pkg_dir
   :version_added: 4.0.0
   :default: {env_dir}/.dist

   Directory where to put project packages.

.. conf::
   :keys: config_settings_get_requires_for_build_sdist
   :version_added: 4.11

   Config settings (``dict[str, str]``) passed to the ``get_requires_for_build_sdist`` backend API endpoint.

.. conf::
   :keys: config_settings_build_sdist
   :version_added: 4.11

   Config settings (``dict[str, str]``) passed to the ``build_sdist`` backend API endpoint.

.. conf::
   :keys: config_settings_get_requires_for_build_wheel
   :version_added: 4.11

   Config settings (``dict[str, str]``) passed to the ``get_requires_for_build_wheel`` backend API endpoint.

.. conf::
   :keys: config_settings_prepare_metadata_for_build_wheel
   :version_added: 4.11

   Config settings (``dict[str, str]``) passed to the ``prepare_metadata_for_build_wheel`` backend API endpoint.

.. conf::
   :keys: config_settings_build_wheel
   :version_added: 4.11

   Config settings (``dict[str, str]``) passed to the ``build_wheel`` backend API endpoint.

.. conf::
   :keys: config_settings_get_requires_for_build_editable
   :version_added: 4.11

   Config settings (``dict[str, str]``) passed to the ``get_requires_for_build_editable`` backend API endpoint.

.. conf::
   :keys: config_settings_prepare_metadata_for_build_editable
   :version_added: 4.11

   Config settings (``dict[str, str]``) passed to the ``prepare_metadata_for_build_editable`` backend API endpoint.

.. conf::
   :keys: config_settings_build_editable
   :version_added: 4.11

   Config settings (``dict[str, str]``) passed to the ``build_editable`` backend API endpoint.

.. conf::
   :keys: fresh_subprocess
   :version_added: 4.14.0
   :default: True if build backend is setuptools otherwise False

   A flag controlling if each call to the build backend should be done in a fresh subprocess or not (especially older
   build backends such as ``setuptools`` might require this to discover newly provisioned dependencies).


Pip installer
~~~~~~~~~~~~~

.. conf::
   :keys: install_command
   :default: python -I -m pip install {opts} {packages}
   :version_added: 1.6

   Determines the command used for installing packages into the virtual environment; both the package under test and its
   dependencies (defined with :ref:`deps`). Must contain the substitution key ``{packages}`` which will be replaced by
   the package(s) to install.  You should also accept ``{opts}`` -- it will contain index server options such as
   ``--pre`` (configured as ``pip_pre``).

   .. note::

      You can also provide arbitrary commands to the ``install_command``. Please take care that these commands can be
      executed on the supported operating systems. When executing shell scripts we recommend to not specify the script
      directly but instead pass it to the appropriate shell as argument (e.g. prefer ``bash script.sh`` over
      ``script.sh``).

.. conf::
   :keys: list_dependencies_command
   :default: python -m pip freeze --all
   :version_added: 2.4

   The ``list_dependencies_command`` setting is used for listing the packages installed into the virtual environment.
   This command will be executed only if executing on Continuous Integrations is detected (for example set environment
   variable ``CI=1``) or if journal is active.


.. conf::
   :keys: pip_pre
   :default: false
   :version_added: 1.9

   If ``true``, adds ``--pre`` to the ``opts`` passed to :ref:`install_command`. This will cause it to install the
   latest available pre-release of any dependencies without a specified version. If ``false``, pip will only install
   final releases of unpinned dependencies.

.. conf::
   :keys: constrain_package_deps
   :default: false
   :version_added: 4.4.0

   If ``constrain_package_deps`` is true, then tox will create and use ``{env_dir}{/}constraints.txt`` when installing
   package dependencies during ``install_package_deps`` stage. When this value is set to false, any conflicting package
   dependencies will override explicit dependencies and constraints passed to ``deps``.

.. conf::
   :keys: use_frozen_constraints
   :default: false
   :version_added: 4.4.0

   When ``use_frozen_constraints`` is true, then tox will use the ``list_dependencies_command`` to enumerate package
   versions in order to create ``{env_dir}{/}constraints.txt``. Otherwise the package specifications explicitly listed
   under ``deps`` (or in requirements / constraints files referenced in ``deps``) will be used as the constraints. If
   ``constrain_package_deps`` is false, then this setting has no effect.

User configuration
------------------

tox allows creation of user level config-file to modify default values of the CLI commands. It is located in the
OS-specific user config directory under ``tox/config.ini`` path, see ``tox --help`` output for exact location. It can be
changed via ``TOX_USER_CONFIG_FILE`` environment variable. Example configuration:

.. code-block:: ini

    [tox]
    skip_missing_interpreters = true


Set CLI flags via environment variables
---------------------------------------
All configuration can be overridden via environment variables too, the naming convention here is ``TOX_<option>``. E.g.
``TOX_WORK_DIR`` sets the ``--workdir`` flag, or ``TOX_OVERRIDE`` sets the ``--override`` flag. For flags accepting more
than one argument, use the ``;`` character to separate these values:

All configuration inside the configuration file may be overwritten via the ``TOX_OVERRIDE``, note in this case the
configuration file and its access (section/table + key) are needed. Here we demonstrate with a ``tox.ini`` file:

.. code-block:: bash

   # set FOO and bar as passed environment variable
   $ env 'TOX_OVERRIDE=testenv.pass_env=FOO,BAR' tox c -k pass_env -e py
   [testenv:py]
   pass_env =
     BAR
     FOO
     <default pass_envs>

.. code-block:: bash

   # append FOO and bar as passed environment variable to the list already defined in
   # the tox configuration
   $ env 'TOX_OVERRIDE=testenv.pass_env+=FOO,BAR' tox c -k pass_env -e py
   [testenv:py]
   pass_env =
     BAR
     FOO
     <pass_envs defined in configuration>
     <default pass_envs>

.. code-block:: bash

   # set httpx and deps to and 3.12 as base_python
   $ env 'TOX_OVERRIDE=testenv.deps=httpx;testenv.base_python=3.12' .tox/dev/bin/tox c \
         -k deps base_python -e py
   [testenv:py]
   deps = httpx
   base_python = 3.12

Overriding configuration from the command line
----------------------------------------------

You can override options in the configuration file, from the command line. For example, given this config:

.. tab:: TOML

   .. code-block:: toml

       # tox.toml
      [env_run_base]
      deps = ["pytest"]
      set_env = { foo = "bar" }
      commands = [[ "pytest", "tests" ]]

.. tab:: INI

   .. code-block:: ini

    [testenv]
    deps = pytest
    set_env =
      foo=bar
    commands = pytest tests

You could enable ``ignore_errors`` by running:

.. tab:: TOML

    .. code-block:: bash

       tox --override env_run_base.ignore_errors=True

.. tab:: INI

    .. code-block:: bash

       tox --override testenv.ignore_errors=True


You could add additional dependencies by running:

.. tab:: TOML

    .. code-block:: bash

       tox --override env_run_base.deps+=pytest-xdist

.. tab:: INI

    .. code-block:: bash

       tox --override testenv.deps+=pytest-xdist

You could set additional environment variables by running:

.. tab:: TOML

    .. code-block:: bash

       tox --override env_run_base.set_env+=baz=quux

.. tab:: INI

    .. code-block:: bash

       tox --override testenv.set_env+=baz=quux

You can specify overrides multiple times on the command line to append multiple items:

.. tab:: TOML

    .. code-block:: bash

       tox -x env_run_base.set_env+=foo=bar -x env_run_base.set_env+=baz=quux
       tox -x testenv_run_baseenv.deps+=pytest-xdist -x env_run_base.deps+=pytest-covt

.. tab:: INI

    .. code-block:: bash

       tox -x testenv.set_env+=foo=bar -x testenv.set_env+=baz=quux
       tox -x testenv.deps+=pytest-xdist -x testenv.deps+=pytest-covt

Or reset override and append to that (note the first override is ``=`` and not ``+=``):

.. tab:: TOML

    .. code-block:: bash

       tox -x env_run_base.deps=pytest-xdist -x env_run_base.deps+=pytest-cov

.. tab:: INI

    .. code-block:: bash

       tox -x testenv.deps=pytest-xdist -x testenv.deps+=pytest-cov

TOML only
---------

These additional rules are active for native TOML configuration files.

String elements (excluding keys) will be transformed according to the :ref:`Substitutions <substitution>` section.

String substitution references
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 4.21

Within strings values from other sections can be referred to via ``{[<table>]<key>}``:

which you can use to avoid repetition of config values. You can put default values in one section and reference them in
others to avoid repeating the same values:

.. code-block:: toml

    [extra]
    ok = "o"
    [.env.B]
    description = "{[extra]ok}"

If the target table is one of the tox environments variable substitution will be applied on the replaced value,
otherwise the text will be inserted as is (e.g., here with extra).

Configuration reference
~~~~~~~~~~~~~~~~~~~~~~~
.. versionadded:: 4.21

You can reference other configurations via the ``ref`` replacement. This can either be of type:


- ``env``, in this case the configuration is loaded from another tox environment, where string substitution will happen
  in that environments scope:

    .. code-block:: toml

        [env.src]
        extras = ["A", "{env_name}"]
        [env.dest]
        extras = [{ replace = "ref", env = "src", key = "extras", extend = true }, "B"]

  In this case ``dest`` environments ``extras`` will be ``A``, ``src``, ``B``.

- ``raw``, in this case the configuration is loaded as raw, and substitution executed in the current environments scope:

    .. code-block:: toml

        [env.src]
        extras = ["A", "{env_name}"]
        [env.dest]
        extras = [{ replace = "ref", of = ["env", "extras"], extend = true }, "B"]

  In this case ``dest`` environments ``extras`` will be ``A``, ``dest``, ``B``.

The ``extend`` flag controls if after replacement the value should be replaced as is in the host structure (when flag is
false -- by default) or be extended into. This flag only operates when the host is a list.

Positional argument reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. versionadded:: 4.21

You can reference positional arguments via the ``posargs`` replacement:

.. code-block:: toml

    [env.A]
    commands = [["python", { replace = "posargs", default = ["a", "b"], extend = true } ]]

If the positional arguments are not set commands will become ``python a b``, otherwise will be ``python posarg-set``.
The ``extend`` option instructs tox to unroll the positional arguments within the host structure. Without it the result
would become ``["python", ["a", "b"]`` which would be invalid.

Note that:

.. code-block:: toml

    [env.A]
    commands = [["python", "{posargs}" ]]

Differs in sense that the positional arguments will be set as a single argument, while in the original example they are
passed through as separate.

Empty commands groups will be ignored:

.. code-block:: toml

    [env.A]
    commands = [[], ["pytest]]

will only invoke pytest. This is especially useful together with posargs allowing you to opt out of running a set of
commands:

  .. code-block:: toml

    [env.A]
    commands = [
        { replace = "posargs", default = ["python", "patch.py"]},
        ["pytest"]
    ]

When running ``tox run -e A`` it will invoke ``python patch.py`` followed by pytest. When running ``tox run -e A --`` it
will invoke only pytest.


Environment variable reference
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. versionadded:: 4.21

You can reference environment variables via the ``env`` replacement:

.. code-block:: toml

    [env.A]
    set_env.COVERAGE_FILE = { replace = "env", name = "COVERAGE_FILE", default = "ok" }

If the environment variable is set the the ``COVERAGE_FILE`` will become that, otherwise will default to ``ok``.

References within set_env
~~~~~~~~~~~~~~~~~~~~~~~~~
.. versionadded:: 4.21.1

When you want to inherit ``set_env`` from another environment you can use the feature that if you pass a list of
dictionaries to ``set_env`` they will be merged together, for example:

.. code-block:: toml

        [tool.tox.env_run_base]
        set_env = { A = "1", B = "2"}

        [tool.tox.env.magic]
        set_env = [
            { replace = "ref", of = ["tool", "tox", "env_run_base", "set_env"]},
            { C = "3", D = "4"},
        ]

Here the ``magic`` tox environment will have both ``A``, ``B``, ``C`` and ``D`` environments set.

INI only
--------
These additional rules are active for native INI configuration.

The value for each setting in an INI configuration will be transformed according to the
:ref:`Substitutions <substitution>` section.

Substitution for values from other sections
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.4

Values from other sections can be referred to via::

   {[sectionname]valuename}

which you can use to avoid repetition of config values. You can put default values in one section and reference them in
others to avoid repeating the same values:

.. code-block:: ini

    [base]
    deps =
        pytest
        mock
        pytest-xdist

    [testenv:dulwich]
    deps =
        dulwich
        {[base]deps}

    [testenv:mercurial]
    deps =
        mercurial
        {[base]deps}

Conditional settings
~~~~~~~~~~~~~~~~~~~~

- Configurations may be set conditionally within the ``tox.ini`` file. If a line starts with an environment name
  or names, separated by a comma, followed by ``:`` the configuration will only be used if the
  environment name(s) matches the executed tox environment. For example:

  .. code-block:: ini

     [testenv]
     deps =
        pip
        format: black
        py310,py39: pytest

  Here pip will be always installed as the configuration value is not conditional. black is only used for the ``format``
  environment, while ``pytest`` is only installed for the ``py310`` and ``py39`` environments.

.. _generative-environment-list:

Generative environment list
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you have a large matrix of dependencies, python versions and/or environments you can use a generative
:ref:`env_list` and conditional settings to express that in a concise form:

.. code-block:: ini

    [tox]
    env_list = py3{9-11}-django{41,40}-{sqlite,mysql}

    [testenv]
    deps =
        django41: Django>=4.1,<4.2
        django40: Django>=4.0,<4.1
        # use PyMySQL if factors "py311" and "mysql" are present in env name
        py311-mysql: PyMySQL
        # use urllib3 if any of "py311" or "py310" are present in env name
        py311,py310: urllib3
        # mocking sqlite on 3.11 and 3.10 if factor "sqlite" is present
        py{311,310}-sqlite: mock

This will generate the following tox environments:

.. code-block:: shell

    > tox l
    default environments:
    py39-django41-sqlite  -> [no description]
    py39-django41-mysql   -> [no description]
    py39-django40-sqlite  -> [no description]
    py39-django40-mysql   -> [no description]
    py310-django41-sqlite -> [no description]
    py310-django41-mysql  -> [no description]
    py310-django40-sqlite -> [no description]
    py310-django40-mysql  -> [no description]
    py311-django41-sqlite -> [no description]
    py311-django41-mysql  -> [no description]
    py311-django40-sqlite -> [no description]
    py311-django40-mysql  -> [no description]

Both enumerations (``{1,2,3}``) and numerical ranges (``{1-3}``) are supported, and can be mixed together:

.. code-block:: ini

    [tox]
    env_list = py3{8-10, 11, 13-14}

will create the following envs:

.. code-block:: shell

    > tox l
    default environments:
    py38  -> [no description]
    py39  -> [no description]
    py310 -> [no description]
    py311 -> [no description]
    py313 -> [no description]
    py314 -> [no description]

Negative ranges will also be expanded (``{3-1}`` -> ``{3,2,1}``), however, open ranges such as ``{1-}``, ``{-2}``, ``{a-}``, and ``{-b}`` will not be expanded.



Generative section names
~~~~~~~~~~~~~~~~~~~~~~~~

Suppose you have some binary packages, and need to run tests both in 32 and 64 bits. You also want an environment to
create your virtual env for the developers.
This also supports ranges in the same way as generative environment lists.

.. code-block:: ini

    [testenv]
    base_python =
        py311-x86: python3.11-32
        py311-x64: python3.11-64
    commands = pytest

    [testenv:py311-{x86,x64}-venv]
    envdir =
        x86: .venv-x86
        x64: .venv-x64

.. code-block:: shell

    > tox l
    default environments:
    py          -> [no description]

    additional environments:
    py311-x86-venv -> [no description]
    py311-x64-venv -> [no description]

.. _substitution:

Substitutions
-------------

**Value substitution** operates through the ``{...}`` string-substitution pattern. The string inside the curly braces
may reference a global or per-environment config key as described above.

In substitutions, the backslash character ``\`` will act as an escape when preceding
``{``, ``}``, ``:``, ``[``, or ``]``, otherwise the backslash will be reproduced literally:

.. tab:: TOML

    .. code-block:: toml

        commands = [
          ["python", "-c", 'print("\{posargs} = \{}".format("{posargs}"))'],
          ["python", "-c", 'print("host: \{}".format("{env:HOSTNAME:host\: not set}")'],
        ]

.. tab:: INI

    .. code-block:: ini

        commands =
          python -c 'print("\{posargs} = \{}".format("{posargs}"))'
          python -c 'print("host: \{}".format("{env:HOSTNAME:host\: not set}")'


Note that any backslashes remaining after substitution may be processed by ``shlex`` during command parsing. On POSIX
platforms, the backslash will escape any following character; on windows, the backslash will escape any following quote,
whitespace, or backslash character (since it normally acts as a path delimiter).

Special substitutions that accept additional colon-delimited ``:`` parameters
cannot have a space after the ``:`` at the beginning of line (e.g.  ``{posargs:
magic}`` would be parsed as factorial ``{posargs``, having value magic).

.. _`environment variable substitutions`:

Environment variable substitutions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you specify a substitution string like this::

    {env:KEY}

then the value will be retrieved as ``os.environ['KEY']`` and replaced with an empty string if the environment variable
does not exist.


Environment variable substitutions with default values
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you specify a substitution string like this::

    {env:KEY:DEFAULTVALUE}

then the value will be retrieved as ``os.environ['KEY']`` and replaced with DEFAULTVALUE if the environment variable does
not exist.

If you specify a substitution string like this::

    {env:KEY:}

then the value will be retrieved as ``os.environ['KEY']`` and replaced with an empty string if the environment variable
does not exist.

Substitutions can also be nested. In that case they are expanded starting from the innermost expression::

    {env:KEY:{env:DEFAULT_OF_KEY}}

the above example is roughly equivalent to ``os.environ.get('KEY', os.environ['DEFAULT_OF_KEY'])``

Interactive shell substitution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 3.4.0

It's possible to inject a config value only when tox is running in interactive shell (standard input)::

    {tty:ON_VALUE:OFF_VALUE}

The first value is the value to inject when the interactive terminal is available, the second value is the value to use
when it's not (optional). A good use case for this is e.g. passing in the ``--pdb`` flag for pytest.

.. _`command positional substitution`:
.. _`positional substitution`:

Substitutions for positional arguments in commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 1.0

If you specify a substitution string like this::

    {posargs:DEFAULTS}

then the value will be replaced with positional arguments as provided to the tox command::

    tox arg1 arg2

In this instance, the positional argument portion will be replaced with ``arg1 arg2``. If no positional arguments were
specified, the value of DEFAULTS will be used instead. If DEFAULTS contains other substitution strings, such as
``{env:*}``, they will be interpreted.,

Use a double ``--`` if you also want to pass options to an underlying test command, for example::

    tox run -e 3.13 -- --opt1 ARG1

will make the ``--opt1 ARG1`` appear in all test commands where ``[]`` or ``{posargs}`` was specified.  By default (see
``args_are_paths`` setting), ``tox`` rewrites each positional argument if it is a relative path and exists on the
filesystem to become a path relative to the ``changedir`` setting.

Other Substitutions
~~~~~~~~~~~~~~~~~~~

* ``{:}`` - replaced as ``os.pathsep``
* ``{/}`` - replaced as ``os.sep``
