.. be in -*- rst -*- mode!

tox configuration specification
===============================

configuration discovery
-----------------------

At the moment tox supports three configuration locations prioritized in the following order:

1. ``pyproject.toml``,
2. ``tox.ini``,
3. ``setup.cfg``.

As far as the configuration format at the moment we only support standard ConfigParser_ "ini-style" format
(there is a plan to add a pure TOML one soon).
``tox.ini`` and ``setup.cfg`` are such files. Note that ``setup.cfg`` requires the content to be under the
``tox:tox`` section. ``pyproject.toml`` on the other hand is in TOML format. However, one can inline
the *ini-style* format under the ``tool.tox.legacy_tox_ini`` key as a multi-line string.

Below you find the specification for the *ini-style* format, but you might want to skim some
:doc:`examples` first and use this page as a reference.

tox global settings
-------------------

Global settings are defined under the ``tox`` section as:

.. code-block:: ini

    [tox]
    minversion = 3.4.0

.. conf:: minversion

   Define the minimal tox version required to run; if the host tox is less than this
   the tool with create an environment and provision it with a tox that satisfies it
   under :conf:`provision_tox_env`.

.. conf:: requires ^ LIST of PEP-508

    .. versionadded:: 3.2.0

    Specify python packages that need to exist alongside the tox installation for the tox build
    to be able to start (must be PEP-508_ compliant). Use this to specify plugin requirements
    (or the version of ``virtualenv`` - determines the default ``pip``, ``setuptools``, and ``wheel``
    versions the tox environments start with). If these dependencies are not specified tox will create
    :conf:`provision_tox_env` environment so that they are satisfied and delegate all calls to that.

    .. code-block:: ini

        [tox]
        requires = tox-venv
                   setuptools >= 30.0.0

.. conf:: provision_tox_env ^ string ^ .tox

    .. versionadded:: 3.8.0

    Name of the virtual environment used to provision a tox having all dependencies specified
    inside :conf:`requires` and :conf:`minversion`.

.. conf:: toxworkdir ^ PATH ^ {toxinidir}/.tox

   Directory for tox to generate its environments into, will be created if it does not exist.

.. conf:: temp_dir ^ PATH ^ {toxworkdir}/.tmp

   Directory where to put tox temporary files. For example: we create a hard link (if possible,
   otherwise new copy) in this directory for the project package. This ensures tox works correctly
   when having parallel runs (as each session will have its own copy of the project package - e.g.
   the source distribution).

.. conf:: skipsdist ^ true|false ^ false

   Flag indicating to perform the packaging operation or not. Set it to ``true`` when using tox for
   an application, instead of a library.

.. conf:: setupdir ^ PATH ^ {toxinidir}

   Indicates where the packaging root file exists (historically the ``setup.py`` for ``setuptools``).
   This will be the working directory when performing the packaging.

.. conf:: distdir ^ PATH ^ {toxworkdir}/dist

   Directory where the packaged source distribution should be put. Note this is cleaned at the start of
   every packaging invocation.

.. conf:: sdistsrc ^ PATH ^ {toxworkdir}/dist

   Do not build the package, but instead use the latest package available under this path.
   You can override it via the command line flag ``--installpkg``.

.. conf:: distshare ^ PATH ^ {homedir}/.tox/distshare

   Folder where the packaged source distribution will be moved, this is not cleaned between packaging
   invocations. On Jenkins (exists ``JENKINS_URL`` or ``HUDSON_URL`` environment variable)
   the default path is ``{toxworkdir}/distshare``.

.. conf:: envlist ^ comma separated values

    Determining the environment list that ``tox`` is to operate on happens in this order (if any is found,
    no further lookups are made):

    * command line option ``-eENVLIST``
    * environment variable ``TOXENV``
    * ``tox.ini`` file's ``envlist``

    .. versionadded:: 3.4.0

        What tox environments are ran during the tox invocation can be further filtered
        via the operating system environment variable ``TOX_SKIP_ENV`` regular expression
        (e.g. ``py27.*`` means **don't** evaluate environments that start with the key ``py27``).
        Skipped environments will be logged at level two verbosity level.

.. conf:: skip_missing_interpreters ^ config|true|false ^ config

    .. versionadded:: 1.7.2

    When skip missing interpreters is ``true`` will force ``tox`` to return success even
    if some of the specified environments were missing. This is useful for some CI
    systems or running on a developer box, where you might only have a subset of
    all your supported interpreters installed but don't want to mark the build as
    failed because of it. As expected, the command line switch always overrides
    this setting if passed on the invocation. Setting it to ``config``
    means that the value is read from the config file.

.. conf:: ignore_basepython_conflict ^ true|false ^ false

    .. versionadded:: 3.1.0

    tox allows setting the python version for an environment via the :conf:`basepython`
    setting. If that's not set tox can set a default value from the environment name (
    e.g. ``py37`` implies Python 3.7). Matching up the python version with the environment
    name has became expected at this point, leading to surprises when some configs don't
    do so. To help with sanity of users a warning will be emitted whenever the environment
    name version does not matches up with this expectation. In a future version of tox,
    this warning will become an error.

    Furthermore, we allow hard enforcing this rule (and bypassing the warning) by setting
    this flag to ``true``. In such cases we ignore the :conf:`basepython` and instead
    always use the base python implied from the Python name. This allows you to
    configure :conf:`basepython` in the global testenv without affecting environments
    that have implied base python versions.

.. conf:: isolated_build ^ true|false ^ false

    .. versionadded:: 3.3.0

    Activate isolated build environment. tox will use a virtual environment to build
    a source distribution from the source tree. For build tools and arguments use
    the ``pyproject.toml`` file as specified in `PEP-517`_ and `PEP-518`_. To specify the
    virtual environment Python version define use the :conf:`isolated_build_env` config
    section.

.. conf:: isolated_build_env ^ string ^ .package

    .. versionadded:: 3.3.0

    Name of the virtual environment used to create a source distribution from the
    source tree.

.. conf:: parallel_show_output ^ bool ^ false

    .. versionadded:: 3.7.0

    If set to True the content of the output will always be shown when running in parallel mode.

.. conf:: depends ^ comma separated values

    .. versionadded:: 3.7.0

    tox environments this depends on. tox will try to run all dependent environments before running this
    environment. Format is same as :conf:`envlist` (allows factor usage).

    .. warning::

       ``depends`` does not pull in dependencies into the run target, for example if you select ``py27,py36,coverage``
       via the ``-e`` tox will only run those three (even if ``coverage`` may specify as ``depends`` other targets too -
       such as ``py27, py35, py36, py37``).


Jenkins override
++++++++++++++++

It is possible to override global settings inside a Jenkins_ instance (
detection is by checking for existence of the ``JENKINS_URL`` environment variable)
by using the ``tox:jenkins`` section:

.. code-block:: ini

    [tox:jenkins]
    commands = ...  # override settings for the jenkins context


tox environment settings
------------------------

Test environments are defined by a:

.. code-block:: ini

    [testenv:NAME]
    commands = ...

section.  The ``NAME`` will be the name of the virtual environment.
Defaults for each setting in this section are looked up in the::

    [testenv]
    commands = ...

``testenv`` default section.

Complete list of settings that you can put into ``testenv*`` sections:

.. conf:: basepython ^ NAME-OR-PATH

    Name or path to a Python interpreter which will be used for creating the virtual environment,
    this determines in practice the python for what we'll create a virtual isolated environment.
    Use this to specify the python version for a tox environment. If not specified, the virtual
    environments factors (e.g. name part) will be used to automatically set one. For example, ``py37``
    means ``python3.7``, ``py3`` means ``python3`` and ``py`` means ``python``.
    :conf:`provision_tox_env` environment does not inherit this setting from the ``toxenv`` section.

    .. versionchanged:: 3.1

        After resolving this value if the interpreter reports back a different version number
        than implied from the name a warning will be printed by default. However, if
        :conf:`ignore_basepython_conflict` is set, the value is ignored and we force the
        ``basepython`` implied from the factor name.


.. conf:: commands ^ ARGVLIST

    The commands to be called for testing. Only execute if :conf:`commands_pre` succeed.

    Each line is interpreted as one command; however a command can be split over
    multiple lines by ending the line with the ``\`` character.

    Commands will execute one by one in sequential fashion until one of them fails (their exit
    code is non-zero) or all of them succeed. The exit code of a command may be ignored (meaning
    they are always considered successful) by prefixing the command with a dash (``-``) - this is
    similar to how ``make`` recipe lines work. The outcome of the environment is considered successful
    only if all commands (these + setup + teardown) succeeded (exit code ignored via the
    ``-`` or success exit code value of zero).

    :note: the virtual environment binary path (the ``bin`` folder within) is prepended to the os ``PATH``,
        meaning commands will first try to resolve to an executable from within the
        virtual environment, and only after that outside of it. Therefore ``python``
        translates as the virtual environments ``python`` (having the same runtime version
        as the :conf:`basepython`), and ``pip`` translates as the virtual environments ``pip``.

.. conf:: commands_pre ^ ARGVLIST

    .. versionadded:: 3.4

    Commands to run before running the :conf:`commands`.
    All evaluation and configuration logic applies from :conf:`commands`.

.. conf:: commands_post ^ ARGVLIST

    .. versionadded:: 3.4

    Commands to run after running the :conf:`commands`. Execute regardless of the outcome of
    both :conf:`commands` and :conf:`commands_pre`.
    All evaluation and configuration logic applies from :conf:`commands`.

.. conf:: install_command ^ ARGV ^ python -m pip install {opts} {packages}

    .. versionadded:: 1.6

    Determines the command used for installing packages into the virtual environment;
    both the package under test and its dependencies (defined with :conf:`deps`).
    Must contain the substitution key ``{packages}`` which will be replaced by the package(s) to
    install.  You should also accept ``{opts}`` if you are using pip -- it will contain index server options
    such as ``--pre`` (configured as ``pip_pre``) and potentially index-options from the
    deprecated :conf:`indexserver` option.

.. conf:: list_dependencies_command ^ ARGV ^ python -m pip freeze

    .. versionadded:: 2.4

    The ``list_dependencies_command`` setting is used for listing
    the packages installed into the virtual environment.

.. conf:: ignore_errors ^ true|false ^ false

    .. versionadded:: 2.0

    If ``false``, a non-zero exit code from one command will abort execution of
    commands for that environment.
    If ``true``, a non-zero exit code from one command will be ignored and
    further commands will be executed.  The overall status will be
    "commands failed", i.e. tox will exit non-zero in case any command failed.

    It may be helpful to note that this setting is analogous to the ``-k`` or
    ``--keep-going`` option of GNU Make.

    Note that in tox 2.0, the default behavior of tox with respect to treating
    errors from commands changed. tox < 2.0 would ignore errors by default. tox
    >= 2.0 will abort on an error by default, which is safer and more typical
    of CI and command execution tools, as it doesn't make sense to run tests if
    installing some prerequisite failed and it doesn't make sense to try to
    deploy if tests failed.

.. conf:: pip_pre ^ true|false ^ false

    .. versionadded:: 1.9

    If ``true``, adds ``--pre`` to the ``opts`` passed to
    :conf:`install_command`. If :conf:`install_command` uses pip, this
    will cause it to install the latest available pre-release of any
    dependencies without a specified version. If ``false``, pip
    will only install final releases of unpinned dependencies.

    Passing the ``--pre`` command-line option to tox will force this to
    ``true`` for all testenvs.

    Don't set this option if your :conf:`install_command` does not use pip.

.. conf:: whitelist_externals ^ MULTI-LINE-LIST

    each line specifies a command name (in glob-style pattern format)
    which can be used in the ``commands`` section without triggering
    a "not installed in virtualenv" warning.  Example: if you use the
    unix ``make`` for running tests you can list ``whitelist_externals=make``
    or ``whitelist_externals=/usr/bin/make`` if you want more precision.
    If you don't want tox to issue a warning in any case, just use
    ``whitelist_externals=*`` which will match all commands (not recommended).

.. conf:: changedir ^ PATH ^ {toxinidir}

    change to this working directory when executing the test command.

.. conf:: deps ^ MULTI-LINE-LIST

    Environment dependencies - installed into the environment ((see :conf:`install_command`) prior
    to project after environment creation. One dependency (a file, a URL or a package name) per
    line. Must be PEP-508_ compliant. All installer commands are executed using the toxinidir_ as the
    current working directory.

    .. code-block:: ini

        [testenv]
        deps =
            pytest
            pytest-cov >= 3.5
            pywin32 >=1.0 ; sys_platform == 'win32'
            octomachinery==0.0.13  # pyup: < 0.1.0 # disable feature updates


    .. versionchanged:: 2.3

    Support for index servers is now deprecated, and it's usage discouraged.

    .. versionchanged:: 3.9

    Comment support on the same line as the dependency. When feeding the content to the install
    tool we'll strip off content (including) from the first comment marker (``#``)
    preceded by one or more space. For example, if a dependency is
    ``octomachinery==0.0.13  # pyup: < 0.1.0 # disable feature updates`` it will be turned into
    just ``octomachinery==0.0.13``.

.. conf:: platform ^ REGEX

    .. versionadded:: 2.0

    A testenv can define a new ``platform`` setting as a regular expression.
    If a non-empty expression is defined and does not match against the
    ``sys.platform`` string the test environment will be skipped.

.. conf:: setenv ^ MULTI-LINE-LIST

    .. versionadded:: 0.9

    Each line contains a NAME=VALUE environment variable setting which
    will be used for all test command invocations as well as for installing
    the sdist package into a virtual environment.

    Notice that when updating a path variable, you can consider the use of
    variable substitution for the current value and to handle path separator.

    .. code-block:: ini

        [testenv]
        setenv   =
            PYTHONPATH = {env:PYTHONPATH}{:}{toxinidir}

.. conf:: passenv ^ SPACE-SEPARATED-GLOBNAMES

    .. versionadded:: 2.0

    A list of wildcard environment variable names which
    shall be copied from the tox invocation environment to the test
    environment when executing test commands.  If a specified environment
    variable doesn't exist in the tox invocation environment it is ignored.
    You can use ``*`` and ``?`` to match multiple environment variables with
    one name.

    Some variables are always passed through to ensure the basic functionality
    of standard library functions or tooling like pip:

    * passed through on all platforms: ``PATH``, ``LANG``, ``LANGUAGE``,
      ``LD_LIBRARY_PATH``, ``PIP_INDEX_URL``
    * Windows: ``SYSTEMDRIVE``, ``SYSTEMROOT``, ``PATHEXT``, ``TEMP``, ``TMP``
       ``NUMBER_OF_PROCESSORS``, ``USERPROFILE``, ``MSYSTEM``
    * Others (e.g. UNIX, macOS): ``TMPDIR``

    You can override these variables with the ``setenv`` option.

    If defined the ``TOX_TESTENV_PASSENV`` environment variable (in the tox
    invocation environment) can define additional space-separated variable
    names that are to be passed down to the test command environment.

    .. versionchanged:: 2.7

        ``PYTHONPATH`` will be passed down if explicitly defined. If
        ``PYTHONPATH`` exists in the host environment but is **not** declared
        in ``passenv`` a warning will be emitted.

.. conf:: recreate ^ true|false ^ false

    Always recreate virtual environment if this option is true.

.. conf:: downloadcache ^ PATH

    **IGNORED** -- Since pip-8 has caching by default this option is now
    ignored.  Please remove it from your configs as a future tox version might
    bark on it.

.. conf:: sitepackages ^ true|false ^ false

    Set to ``true`` if you want to create virtual environments that also
    have access to globally installed packages.

    .. warning::

      In cases where a command line tool is also installed globally you have
      to make sure that you use the tool installed in the virtualenv by using
      ``python -m <command line tool>`` (if supported by the tool) or
      ``{envbindir}/<command line tool>``.

      If you forget to do that you will get a warning like this::

        WARNING: test command found but not installed in testenv
            cmd: /path/to/parent/interpreter/bin/<some command>
            env: /foo/bar/.tox/python
        Maybe you forgot to specify a dependency? See also the whitelist_externals envconfig setting.


.. conf:: alwayscopy ^ true|false ^ false

    Set to ``true`` if you want virtualenv to always copy files rather than
    symlinking.

    This is useful for situations where hardlinks don't work (e.g. running in
    VMS with Windows guests).

.. conf:: args_are_paths ^ true|false ^ false

    Treat positional arguments passed to ``tox`` as file system paths
    and - if they exist on the filesystem - rewrite them according
    to the ``changedir``. Default is true due to the exists-on-filesystem check it's
    usually safe to try rewriting.

.. conf:: envtmpdir ^ PATH ^ {envdir}/tmp

    Defines a temporary directory for the virtualenv which will be cleared
    each time before the group of test commands is invoked.

.. conf:: envlogdir ^ PATH ^ {envdir}/log

    Defines a directory for logging where tox will put logs of tool
    invocation.

.. conf:: indexserver ^ URL

    .. versionadded:: 0.9

    (DEPRECATED, will be removed in a future version) Multi-line ``name =
    URL`` definitions of python package servers.  Dependencies can
    specify using a specified index server through the
    ``:indexservername:depname`` pattern.  The ``default`` indexserver
    definition determines where unscoped dependencies and the sdist install
    installs from.  Example:

    .. code-block:: ini

        [tox]
        indexserver =
            default = https://mypypi.org

    will make tox install all dependencies from this PyPI index server
    (including when installing the project sdist package).

.. conf:: envdir ^ PATH ^ {toxworkdir}/{envname}

    .. versionadded:: 1.5

    User can set specific path for environment. If path would not be absolute
    it would be treated as relative to ``{toxinidir}``.

.. conf:: usedevelop ^ true|false ^ false

    .. versionadded:: 1.6

    Install the current package in development mode with "setup.py
    develop" instead of installing from the ``sdist`` package. (This
    uses pip's ``-e`` option, so should be avoided if you've specified a
    custom :conf:`install_command` that does not support ``-e``).

.. conf:: skip_install ^ true|false ^ false

    .. versionadded:: 1.9

    Do not install the current package. This can be used when you need the
    virtualenv management but do not want to install the current package
    into that environment.

.. conf:: ignore_outcome ^ true|false ^ false

    .. versionadded:: 2.2

    If set to true a failing result of this testenv will not make tox fail,
    only a warning will be produced.

.. conf:: extras ^ MULTI-LINE-LIST

    .. versionadded:: 2.4

    A list of "extras" to be installed with the sdist or develop install.
    For example, ``extras = testing`` is equivalent to ``[testing]`` in a
    ``pip install`` command. These are not installed if ``skip_install`` is
    ``true``.

.. conf:: description ^ SINGLE-LINE-TEXT ^ no description

    A short description of the environment, this will be used to explain
    the environment to the user upon listing environments for the command
    line with any level of verbosity higher than zero.

Substitutions
-------------

Any ``key=value`` setting in an ini-file can make use
of value substitution through the ``{...}`` string-substitution pattern.

You can escape curly braces with the ``\`` character if you need them, for example::

    commands = echo "\{posargs\}" = {posargs}


Note some substitutions (e.g. ``posargs``, ``env``) may have addition values attached to it,
via the ``:`` character (e.g. ``posargs`` - default value, ``env`` - key).
Such substitutions cannot have a space after the ``:`` character
(e.g. ``{posargs: magic}`` while being at the start of a line
inside the ini configuration (this would be parsed as factorial ``{posargs``,
having value magic).

Globally available substitutions
++++++++++++++++++++++++++++++++

.. _`toxinidir`:

``{toxinidir}``
    the directory where ``tox.ini`` is located

.. _`toxworkdir`:

``{toxworkdir}``
    the directory where virtual environments are created and sub directories
    for packaging reside.

``{homedir}``
    the user-home directory path.

``{distdir}``
    the directory where sdist-packages will be created in

``{distshare}``
    (DEPRECATED) the directory where sdist-packages will be copied to so that
    they may be accessed by other processes or tox runs.

``{:}``
    OS-specific path separator (``:`` os \*nix family, ``;`` on Windows). May be used in ``setenv``,
    when target variable is path variable (e.g. PATH or PYTHONPATH).

substitutions for virtualenv-related sections
+++++++++++++++++++++++++++++++++++++++++++++

``{envname}``
    the name of the virtual environment
``{envpython}``
    path to the virtual Python interpreter
``{envdir}``
    directory of the virtualenv hierarchy
``{envbindir}``
    directory where executables are located
``{envsitepackagesdir}``
    directory where packages are installed.
    Note that architecture-specific files may appear in a different directory.
``{envtmpdir}``
    the environment temporary directory
``{envlogdir}``
    the environment log directory


environment variable substitutions
++++++++++++++++++++++++++++++++++

If you specify a substitution string like this::

    {env:KEY}

then the value will be retrieved as ``os.environ['KEY']``
and raise an Error if the environment variable
does not exist.


environment variable substitutions with default values
++++++++++++++++++++++++++++++++++++++++++++++++++++++

If you specify a substitution string like this::

    {env:KEY:DEFAULTVALUE}

then the value will be retrieved as ``os.environ['KEY']``
and replace with DEFAULTVALUE if the environment variable does not
exist.

If you specify a substitution string like this::

    {env:KEY:}

then the value will be retrieved as ``os.environ['KEY']``
and replace with an empty string if the environment variable does not
exist.

Substitutions can also be nested. In that case they are expanded starting
from the innermost expression::

    {env:KEY:{env:DEFAULT_OF_KEY}}

the above example is roughly equivalent to
``os.environ.get('KEY', os.environ['DEFAULT_OF_KEY'])``

.. _`command positional substitution`:
.. _`positional substitution`:

interactive shell substitution
++++++++++++++++++++++++++++++

It's possible to inject a config value only when tox is running in interactive shell (standard input):

    {tty:ON_VALUE:OFF_VALUE}

The first value is the value to inject when the interactive terminal is available,
the second value is the value to use when it's not. The later on is optional. A good use case
for this is e.g. passing in the ``--pdb`` flag for pytest.

substitutions for positional arguments in commands
++++++++++++++++++++++++++++++++++++++++++++++++++

.. versionadded:: 1.0

If you specify a substitution string like this::

    {posargs:DEFAULTS}

then the value will be replaced with positional arguments as provided
to the tox command::

    tox arg1 arg2

In this instance, the positional argument portion will be replaced with
``arg1 arg2``. If no positional arguments were specified, the value of
DEFAULTS will be used instead. If DEFAULTS contains other substitution
strings, such as ``{env:*}``, they will be interpreted.,

Use a double ``--`` if you also want to pass options to an underlying
test command, for example::

    tox -- --opt1 ARG1

will make the ``--opt1 ARG1`` appear in all test commands where ``[]`` or
``{posargs}`` was specified.  By default (see ``args_are_paths``
setting), ``tox`` rewrites each positional argument if it is a relative
path and exists on the filesystem to become a path relative to the
``changedir`` setting.

Previous versions of tox supported the ``[.*]`` pattern to denote
positional arguments with defaults. This format has been deprecated.
Use ``{posargs:DEFAULTS}`` to specify those.


Substitution for values from other sections
+++++++++++++++++++++++++++++++++++++++++++

.. versionadded:: 1.4

Values from other sections can be referred to via::

   {[sectionname]valuename}

which you can use to avoid repetition of config values.
You can put default values in one section and reference them in others to avoid repeating the same values:

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


Generating environments, conditional settings
---------------------------------------------

.. versionadded:: 1.8

Suppose you want to test your package against python2.7, python3.6 and against
several versions of a dependency, say Django 1.5 and Django 1.6. You can
accomplish that by writing down 2*2 = 4 ``[testenv:*]`` sections and then
listing all of them in ``envlist``.

However, a better approach looks like this:

.. code-block:: ini

    [tox]
    envlist = {py27,py36}-django{15,16}

    [testenv]
    deps =
        pytest
        django15: Django>=1.5,<1.6
        django16: Django>=1.6,<1.7
        py36: unittest2
    commands = pytest

This uses two new facilities of tox-1.8:

- generative envlist declarations where each envname
  consists of environment parts or "factors"

- "factor" specific settings

Let's go through this step by step.


.. _generative-envlist:

Generative envlist
+++++++++++++++++++++++

::

    envlist = {py36,py27}-django{15,16}

This is bash-style syntax and will create ``2*2=4`` environment names
like this::

    py27-django15
    py27-django16
    py36-django15
    py36-django16

You can still list environments explicitly along with generated ones::

    envlist = {py27,py36}-django{15,16}, docs, flake

Keep in mind that whitespace characters (except newline) within ``{}``
are stripped, so the following line defines the same environment names::

    envlist = {py27,py36}-django{ 15, 16 }, docs, flake

.. note::

    To help with understanding how the variants will produce section values,
    you can ask tox to show their expansion with a new option::

        $ tox -l
        py27-django15
        py27-django16
        py36-django15
        py36-django16
        docs
        flake


.. _factors:

Factors and factor-conditional settings
++++++++++++++++++++++++++++++++++++++++

Parts of an environment name delimited by hyphens are called factors and can
be used to set values conditionally. In list settings such as ``deps`` or
``commands`` you can freely intermix optional lines with unconditional ones:

.. code-block:: ini

    [testenv]
    deps =
        pytest
        django15: Django>=1.5,<1.6
        django16: Django>=1.6,<1.7
        py36: unittest2

Reading it line by line:

- ``pytest`` will be included unconditionally,
- ``Django>=1.5,<1.6`` will be included for environments containing
  ``django15`` factor,
- ``Django>=1.6,<1.7`` similarly depends on ``django16`` factor,
- ``unittest`` will be loaded for Python 3.6 environments.

tox provides a number of default factors corresponding to Python interpreter
versions. The conditional setting above will lead to either ``python3.6`` or
``python2.7`` used as base python, e.g. ``python3.6`` is selected if current
environment contains ``py36`` factor.

.. note::

    Configuring :conf:`basepython` for environments using default factors
    will result in a warning. Configure :conf:`ignore_basepython_conflict`
    if you wish to explicitly ignore these conflicts, allowing you to define a
    global :conf:`basepython` for all environments *except* those with
    default factors.

Complex factor conditions
+++++++++++++++++++++++++

Sometimes you need to specify the same line for several factors or create a
special case for a combination of factors. Here is how you do it:

.. code-block:: ini

    [tox]
    envlist = py{27,34,36}-django{15,16}-{sqlite,mysql}

    [testenv]
    deps =
        py34-mysql: PyMySQL     # use if both py34 and mysql are in the env name
        py27,py36: urllib3      # use if either py36 or py27 are in the env name
        py{27,36}-sqlite: mock  # mocking sqlite in python 2.x & 3.6
        !py34-sqlite: mock      # mocking sqlite, except in python 3.4
        sqlite-!py34: mock      # (same as the line above)

Take a look at the first ``deps`` line. It shows how you can special case
something for a combination of factors, by just hyphenating the combining
factors together. This particular line states that ``PyMySQL`` will be loaded
for python 3.4, mysql environments, e.g. ``py34-django15-mysql`` and
``py34-django16-mysql``.

The second line shows how you use the same setting for several factors - by
listing them delimited by commas. It's possible to list not only simple factors,
but also their combinations like ``py27-sqlite,py36-sqlite``.

The remaining lines all have the same effect and use conditions equivalent to
``py27-sqlite,py36-sqlite``. They have all been added only to help demonstrate
the following:

- how factor expressions get expanded the same way as in envlist
- how to use negated factor conditions by prefixing negated factors with ``!``
- that the order in which factors are hyphenated together does not matter

.. note::

    Factors don't do substring matching against env name, instead every
    hyphenated expression is split by ``-`` and if ALL of its non-negated
    factors and NONE of its negated ones are also factors of an env then that
    condition is considered to hold for that env.

    For example, environment ``py36-mysql-!dev``:

    - would be matched by expressions ``py36``, ``py36-mysql`` or
      ``mysql-py36``,
    - but not ``py2``, ``py36-sql`` or ``py36-mysql-dev``.

Factors and values substitution are compatible
++++++++++++++++++++++++++++++++++++++++++++++

It is possible to mix both values substitution and factor expressions.
For example::

    [tox]
    envlist = py27,py36,coverage

    [testenv]
    deps =
        flake8
        coverage: coverage

    [testenv:py27]
    deps =
        {[testenv]deps}
        pytest

With the previous configuration, it will install:

- ``flake8`` and ``pytest`` packages for ``py27`` environment.
- ``flake8`` package for ``py36`` environment.
- ``flake8`` and ``coverage`` packages for ``coverage`` environment.

Advanced settings
-----------------

.. _`long interpreter directives`:

Handle interpreter directives with long lengths
+++++++++++++++++++++++++++++++++++++++++++++++

For systems supporting executable text files (scripts with a shebang), the
system will attempt to parse the interpreter directive to determine the program
to execute on the target text file. When ``tox`` prepares a virtual environment
in a file container which has a large length (e.x. using Jenkins Pipelines), the
system might not be able to invoke shebang scripts which define interpreters
beyond system limits (e.x. Linux as a limit of 128; ``BINPRM_BUF_SIZE``). To
workaround an environment which suffers from an interpreter directive limit, a
user can bypass the system's interpreter parser by defining the
``TOX_LIMITED_SHEBANG`` environment variable before invoking ``tox``::

    export TOX_LIMITED_SHEBANG=1

When the workaround is enabled, all tox-invoked text file executables will have
their interpreter directive parsed by and explicitly executed by ``tox``.

Injected environment variables
------------------------------
tox will inject the following environment variables that you can use to test that your command is running within tox:

.. versionadded:: 3.4

- ``TOX_WORK_DIR`` env var is set to the tox work directory
- ``TOX_ENV_NAME`` is set to the current running tox environment name
- ``TOX_ENV_DIR`` is set to the current tox environments working dir.
- ``TOX_PACKAGE`` the packaging phases outcome path (useful to inspect and make assertion of the built package itself).
- ``TOX_PARALLEL_ENV`` is set to the current running tox environment name, only when running in parallel mode.

:note: this applies for all tox envs (isolated packaging too) and all external
 commands called (e.g. install command - pip).

Other Rules and notes
---------------------

* ``path`` specifications: if a specified ``path`` is a relative path
  it will be considered as relative to the ``toxinidir``, the directory
  where the configuration file resides.

cli
===

.. autoprogram:: tox.cli:cli
   :prog: tox

.. include:: links.rst
