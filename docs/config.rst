Configuration
+++++++++++++

tox configuration can be split into two categories: core and environment specific. Core settings are options that can
be set once and used for all tox environments, while environment options are applied to the given tox environment only.

Discovery and file types
------------------------

Out of box tox supports three configuration locations prioritized in the following order:

1. ``tox.ini``,
2. ``pyproject.toml``,
3. ``setup.cfg``.

As far as the configuration format at the moment we only support a *ini-style*. ``tox.ini`` and ``setup.cfg`` are by
nature such file, while in ``pyprojec.toml`` currently you can only inline the *ini-style* config.

Note that ``setup.cfg`` requires the content to be under the ``tox:tox`` and ``testenv`` sections and is otherwise
ignored. ``pyproject.toml`` on the other hand is in TOML format. However, one can inline the *ini-style* format under
the ``tool.tox.legacy_tox_ini`` key as a multi-line string.

``tox.ini``
~~~~~~~~~~~
The core settings are under the ``tox`` section while the environment sections are under the ``testenv:{env_name}``
section. All tox environments by default inherit setting from the ``testenv`` section. This means if tox needs an option
and is not available under ``testenv:{env_name}`` will first try to use the value from ``testenv``, before falling back
to the default value for that setting. For example:

.. code-block:: ini

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

``setup.cfg``
~~~~~~~~~~~~~
The core settings are under the ``tox:tox`` section while the environment sections are under the ``testenv:{env_name}``
section. All tox environments by default inherit setting from the ``testenv`` section. This means if tox needs an option
and is not available under ``testenv:{env_name}`` will first try to use the value from ``testenv``, before falling back
to the default value for that setting. For example:

.. code-block:: ini

    [tox:tox]
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

``pyproject.toml``
~~~~~~~~~~~~~~~~~~
You can inline a ``tox.ini`` style configuration under the ``tool:tox`` section and ``legacy_tox_ini`` key.

Below you find the specification for the *ini-style* format, but you might want to skim some
examples first and use this page as a reference.

.. code-block:: toml

    [tool:tox]
    legacy_tox_ini = """
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

Core
----

.. conf::
   :keys: requires
   :default: <empty list>
   :version_added: 3.2.0

   Specify a list of `PEP-508 <https://www.python.org/dev/peps/pep-0508/>`_ compliant dependencies that must be
   satisfied in the python environment hosting tox when running the tox command. If any of these dependencies are not
   satisfied will automatically create a provisioned tox environment that does not have this issue, and run the tox
   command within that environment. See :ref:`provision_tox_env` for more details.

   .. code-block:: ini

        [tox]
        requires =
            tox>4
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
   :default: {tox_root}/.tmp

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


tox environment
---------------

Base
~~~~

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
   :keys: platform

   Run on platforms that match this regular expression (empty means any platform). If a non-empty expression is defined
   and does not match against the ``sys.platform`` string the entire test environment will be skipped and none of the
   commands will be executed. Running ``tox -e <platform_name>`` will run commands for a particular platform and skip
   the rest.

.. conf::
   :keys: pass_env, passenv
   :default: <empty list>

   Environment variables to pass on to the tox environment. You can use the ``*`` to express wildcard expressions, e.g.
   ``PIP_*`` translates to all environment variables that start with the ``PIP_`` characters.  If a specified
   environment variable doesn't exist in the tox invocation environment it is ignored. The list of environment variable
   names is not case sensitive, and all variables that match when upper cased will be passed. For example, passing ``A``
   will pass both ``A`` and ``a``.

.. conf::
   :keys: set_env, setenv

   A dictionary of environment variables to set when running commands in the tox environment.

.. conf::
   :keys: parallel_show_output
   :default: False
    :version_added: 3.7

   If set to ``True`` the content of the output will always be shown  when running in parallel mode.

.. conf::
   :keys: recreate
   :default: False

   Always recreate virtual environment if this option is true, otherwise leave it up to tox.

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

     Inline scripts can be used, however note these are discovered from the project root directory, and is not
     influenced by :ref:`change_dir` (this only affects the runtime current working directory). To make this behaviour
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
   :default: {tox root}

   Change to this working directory when executing the test command. If the directory does not exist yet, it will be
   created (required for Windows to be able to execute any command).


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

   Tox package type used to package.

Package
~~~~~~~
.. conf::
   :keys: package_root, setupdir
   :default: {package_root}
   :ref_suffix: env

   Indicates where the packaging root file exists (historically setup.py file or pyproject.toml now).


Python
~~~~~~
.. conf::
   :keys: base_python, basepython
   :default: {package_root}

   Name or path to a Python interpreter which will be used for creating the virtual environment, first one found wins.
   This determines in practice the python for what we'll create a virtual isolated environment. Use this to specify the
   python version for a tox environment. If not specified, the virtual environments factors (e.g. name part) will be
   used to automatically set one. For example, ``py310`` means ``python3.10``, ``py3`` means ``python3`` and ``py``
   means ``python``.

    .. versionchanged:: 3.1

        After resolving this value if the interpreter reports back a different version number than implied from the name
        a warning will be printed by default. However, if :ref:`ignore_basepython_conflict` is set, the value is
        ignored and we force the :ref:`base_python` implied from the factor name.

.. conf::
   :keys: ignore_base_python_conflict, ignore_basepython_conflict
   :default: True

    .. versionadded:: 3.1.0

    tox allows setting the python version for an environment via the :ref:`basepython` setting. If that's not set tox
    can set a default value from the environment name (e.g. ``py310`` implies Python 3.10). Matching up the python
    version with the environment name has became expected at this point, leading to surprises when some configs don't
    do so. To help with sanity of users a error will be raised whenever the environment name version does not matches
    up with this expectation.

    Furthermore, we allow hard enforcing this rule (and bypassing the warning) by setting this flag to ``true``. In such
    cases we ignore the :ref:`base_python` and instead always use the base python implied from the Python name. This
    allows you to configure :ref:`base_python` in the :ref:`base` section without affecting environments that have
    implied base python versions.

.. conf::
   :keys: env_site_packages_dir, envsitepackagesdir
   :constant:

   The python environments site package - where packages are installed (the purelib folder path).

.. conf::
   :keys: env_bin_dir, envbindir
   :constant:

   The binary folder where console/gui scripts are generated during installation.

.. conf::
   :keys: env_python, envpython
   :constant:

   The python executable from within the tox environment.

Python run
~~~~~~~~~~
.. conf::
   :keys: deps
   :default: <empty list>

   Name of the python dependencies as specified by `PEP-440`_. Installed into the environment prior to project after
   environment creation, but before package installation. All installer commands are executed using the :ref:`tox_root`
   as the current working directory.

.. conf::
   :keys: use_develop, usedevelop
   :default: false
   :version_added: 1.6

   Install the current package in development mode with develop mode. For pip this uses ``-e`` option, so should be
   avoided if you've specified a custom :ref:`install_command` that does not support ``-e``.

.. conf::
   :keys: package
   :version_added: 4.0

   When option can be one of ``skip``, ``dev-legacy``, ``sdist`` or ``wheel``. If :ref:`use_develop` is set this becomes
   a constant of ``dev-legacy``. If :ref:`skip_install` is set this becomes a constant of ``skip``.


.. conf::
   :keys: wheel_build_env
   :version_added: 4.0
   :default: <package_env>-<python-flavor-lowercase><python-version-no-dot>

   If :ref:`wheel_build_env` is set to ``wheel`` this will be the tox Python environment in which the wheel will be
   built. The value is generated to be unique per python flavor and version, and prefixed with :ref:`package_env` value.
   This is to ensure the target interpreter and the generated wheel will be compatible. If you have a wheel that can be
   reused across multiple python versions set this value to the same across them (to avoid building a new wheel for
   each one of them).

.. conf::
   :keys: extras
   :version_added: 2.4
   :default: <empty list>

   A list of "extras" from the package to be installed. For example, ``extras = testing`` is equivalent to ``[testing]``
   in a ``pip install`` command.

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
     ``{env_bin_dir}/<command line tool>``. If you forget to do that you will get a warning like this:

      .. code-block::

         WARNING: test command found but not installed in testenv
             cmd: /path/to/parent/interpreter/bin/<some command>
             env: /foo/bar/.tox/python
         Maybe you forgot to specify a dependency? See also the allowlist_externals envconfig settin

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

Pip installer
~~~~~~~~~~~~~

.. conf::
   :keys: install_command
   :default: python -I -m pip install <opts> <packages>
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


.. conf::
   :keys: pip_pre
   :default: false
   :version_added: 1.9

   If ``true``, adds ``--pre`` to the ``opts`` passed to :ref:`install_command`. This will cause it to install the
   latest available pre-release of any dependencies without a specified version. If ``false``, pip will only install
   final releases of unpinned dependencies.

.. _`PEP-508`: https://www.python.org/dev/peps/pep-0508/
.. _`PEP-440`: https://www.python.org/dev/peps/pep-0440/
