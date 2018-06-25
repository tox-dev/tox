.. be in -*- rst -*- mode!

tox configuration specification
===============================

.. _ConfigParser: https://docs.python.org/3/library/configparser.html

``tox.ini`` files uses the standard ConfigParser_ "ini-style" format.
Below you find the specification, but you might want to skim some
:doc:`examples` first and use this page as a reference.

tox global settings
-------------------

List of optional global options:

.. code-block:: ini

    [tox]
    minversion=ver    # minimally required tox version
    toxworkdir=path   # tox working directory, defaults to {toxinidir}/.tox
    setupdir=path     # defaults to {toxinidir}
    distdir=path      # defaults to {toxworkdir}/dist
    distshare=path    # (DEPRECATED) defaults to {homedir}/.tox/distshare
    envlist=ENVLIST   # defaults to the list of all environments
    skipsdist=BOOL    # defaults to false


``tox`` autodetects if it is running in a Jenkins_ context
(by checking for existence of the ``JENKINS_URL`` environment variable)
and will first lookup global tox settings in this section:

.. code-block:: ini

    [tox:jenkins]
    ...               # override [tox] settings for the jenkins context
    # note: for jenkins distshare defaults to ``{toxworkdir}/distshare`` (DEPRECATED)

.. confval:: skip_missing_interpreters=BOOL

    .. versionadded:: 1.7.2

    Setting this to ``True`` is equivalent of passing the
    ``--skip-missing-interpreters`` command line option, and will force ``tox`` to
    return success even if some of the specified environments were missing. This is
    useful for some CI systems or running on a developer box, where you might only
    have a subset of all your supported interpreters installed but don't want to
    mark the build as failed because of it. As expected, the command line switch
    always overrides this setting if passed on the invokation.
    **Default:** ``False``

.. confval:: envlist=CSV

    Determining the environment list that ``tox`` is to operate on
    happens in this order (if any is found, no further lookups are made):

    * command line option ``-eENVLIST``
    * environment variable ``TOXENV``
    * ``tox.ini`` file's ``envlist``

.. confval:: ignore_basepython_conflict=True|False(default)

    .. versionadded:: 3.1.0

    If ``True``, :confval:`basepython` settings that conflict with the Python
    variant for a environments using default factors, such as ``py27`` or
    ``py35``, will be ignored. This allows you to configure
    :confval:`basepython` in the global testenv without affecting these
    factors. If ``False``, the default, a warning will be emitted if a conflict
    is identified. In a future version of tox, this warning will become an
    error.

.. confval:: build=sdist|wheel|none

    .. versionadded:: 3.1.0

    tox will try to build the project as a Python package and install it in a fresh virtual
    environment before running your test commands. Here one can select the type of build
    tox will do for the projects package:

    - if it's ``none`` tox will not try to build the package (implies no install happens later),
    - if it's ``sdist`` it will create a source distribution by using ``distutils``:

        .. code-block:: ini

            python setup.py sdist

    - if it's ``wheel`` it will create a Python wheel by using ``pip``:

        .. code-block:: ini

            pip build wheel --no-dep


    **Default:** ``sdist``



Virtualenv test environment settings
------------------------------------

Test environments are defined by a:

.. code-block:: ini

    [testenv:NAME]
    ...

section.  The ``NAME`` will be the name of the virtual environment.
Defaults for each setting in this section are looked up in the::

    [testenv]
    ...

testenvironment default section.

Complete list of settings that you can put into ``testenv*`` sections:

.. confval:: basepython=NAME-OR-PATH

    Name or path to a Python interpreter which will be used for creating
    the virtual environment; if the environment name contains a :ref:`default
    factor <factors>`, this value will be ignored. **default**: interpreter
    used for tox invocation.

    .. versionchanged:: 3.1

       Environments that use a :ref:`default factor <factors>` now ignore this
       value, defaulting to the interpreter defined for that factor.

.. confval:: commands=ARGVLIST

    The commands to be called for testing. Each command is defined
    by one or more lines; a command can have multiple lines if a line
    ends with the ``\`` character in which case the subsequent line
    will be appended (and may contain another ``\`` character ...).
    For eventually performing a call to ``subprocess.Popen(args, ...)``
    ``args`` are determined by splitting the whole command by whitespace.
    Similar to ``make`` recipe lines, any command with a leading ``-``
    will ignore the exit code.

.. confval:: install_command=ARGV

    .. versionadded:: 1.6

    The ``install_command`` setting is used for installing packages into
    the virtual environment; both the package under test
    and its dependencies (defined with :confval:`deps`).
    Must contain the substitution key
    ``{packages}`` which will be replaced by the packages to
    install.  You should also accept ``{opts}`` if you are using
    pip -- it will contain index server options
    such as ``--pre`` (configured as ``pip_pre``) and potentially
    index-options from the deprecated :confval:`indexserver`
    option.

    **default**::

        pip install {opts} {packages}

.. confval:: list_dependencies_command

    .. versionadded:: 2.4

    The ``list_dependencies_command`` setting is used for listing
    the packages installed into the virtual environment.

    **default**::

        pip freeze

.. confval:: ignore_errors=True|False(default)

    .. versionadded:: 2.0

    If ``True``, a non-zero exit code from one command will be ignored and
    further commands will be executed (which was the default behavior in tox <
    2.0).  If ``False`` (the default), then a non-zero exit code from one
    command will abort execution of commands for that environment.

    It may be helpful to note that this setting is analogous to the ``-i`` or
    ``ignore-errors`` option of GNU Make. A similar name was chosen to reflect
    the similarity in function.

    Note that in tox 2.0, the default behavior of tox with respect to treating
    errors from commands changed. tox < 2.0 would ignore errors by default. tox
    >= 2.0 will abort on an error by default, which is safer and more typical
    of CI and command execution tools, as it doesn't make sense to run tests if
    installing some prerequisite failed and it doesn't make sense to try to
    deploy if tests failed.

.. confval:: pip_pre=True|False(default)

    .. versionadded:: 1.9

    If ``True``, adds ``--pre`` to the ``opts`` passed to
    :confval:`install_command`. If :confval:`install_command` uses pip, this
    will cause it to install the latest available pre-release of any
    dependencies without a specified version. If ``False`` (the default), pip
    will only install final releases of unpinned dependencies.

    Passing the ``--pre`` command-line option to tox will force this to
    ``True`` for all testenvs.

    Don't set this option if your :confval:`install_command` does not use pip.

.. confval:: whitelist_externals=MULTI-LINE-LIST

    each line specifies a command name (in glob-style pattern format)
    which can be used in the ``commands`` section without triggering
    a "not installed in virtualenv" warning.  Example: if you use the
    unix ``make`` for running tests you can list ``whitelist_externals=make``
    or ``whitelist_externals=/usr/bin/make`` if you want more precision.
    If you don't want tox to issue a warning in any case, just use
    ``whitelist_externals=*`` which will match all commands (not recommended).

.. confval:: changedir=path

    change to this working directory when executing the test command.

    **default**: ``{toxinidir}``

.. confval:: deps=MULTI-LINE-LIST

    Test-specific dependencies - to be installed into the environment prior to project
    package installation.  Each line defines a dependency, which will be
    passed to the installer command for processing (see :confval:`indexserver`).
    Each line specifies a file, a URL or a package name.  You can additionally specify
    an :confval:`indexserver` to use for installing this dependency
    but this functionality is deprecated since tox-2.3.
    All derived dependencies (deps required by the dep) will then be
    retrieved from the specified indexserver:

    .. code-block:: ini

        deps = :myindexserver:pkg

    (Experimentally introduced in 1.6.1) all installer commands are executed
    using the ``{toxinidir}`` as the current working directory.

.. confval:: platform=REGEX

    .. versionadded:: 2.0

    A testenv can define a new ``platform`` setting as a regular expression.
    If a non-empty expression is defined and does not match against the
    ``sys.platform`` string the test environment will be skipped.

.. confval:: setenv=MULTI-LINE-LIST

    .. versionadded:: 0.9

    Each line contains a NAME=VALUE environment variable setting which
    will be used for all test command invocations as well as for installing
    the sdist package into a virtual environment.

.. confval:: passenv=SPACE-SEPARATED-GLOBNAMES

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

.. confval:: recreate=True|False(default)

    Always recreate virtual environment if this option is True.

.. confval:: downloadcache=path

    **IGNORED** -- Since pip-8 has caching by default this option is now
    ignored.  Please remove it from your configs as a future tox version might
    bark on it.

.. confval:: sitepackages=True|False

    Set to ``True`` if you want to create virtual environments that also
    have access to globally installed packages.

    **default:** False, meaning that virtualenvs will be
    created without inheriting the global site packages.

.. confval:: alwayscopy=True|False

    Set to ``True`` if you want virtualenv to always copy files rather than
    symlinking.

    This is useful for situations where hardlinks don't work (e.g. running in
    VMS with Windows guests).

    **default:** False, meaning that virtualenvs will make use of symbolic links.

.. confval:: args_are_paths=BOOL

    Treat positional arguments passed to ``tox`` as file system paths
    and - if they exist on the filesystem - rewrite them according
    to the ``changedir``.

    **default**: True (due to the exists-on-filesystem check it's
    usually safe to try rewriting).

.. confval:: envtmpdir=path

    Defines a temporary directory for the virtualenv which will be cleared
    each time before the group of test commands is invoked.

    **default**: ``{envdir}/tmp``

.. confval:: envlogdir=path

    Defines a directory for logging where tox will put logs of tool
    invocation.

    **default**: ``{envdir}/log``

.. confval:: indexserver

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
            default = http://mypypi.org

    will make tox install all dependencies from this PYPI index server
    (including when installing the project sdist package).

.. confval:: envdir

    .. versionadded:: 1.5

    User can set specific path for environment. If path would not be absolute
    it would be treated as relative to ``{toxinidir}``.

    **default**: ``{toxworkdir}/{envname}``

.. confval:: usedevelop=BOOL

    .. versionadded:: 1.6

    Install the current package in development mode with "setup.py
    develop" instead of installing from the ``sdist`` package. (This
    uses pip's `-e` option, so should be avoided if you've specified a
    custom :confval:`install_command` that does not support ``-e``).

    **default**: ``False``

.. confval:: skip_install=BOOL

    .. versionadded:: 1.9

    Do not install the current package. This can be used when you need the
    virtualenv management but do not want to install the current package
    into that environment.

    **default**: ``False``

.. confval:: ignore_outcome=BOOL

    .. versionadded:: 2.2

    If set to True a failing result of this testenv will not make tox fail,
    only a warning will be produced.

    **default**: ``False``

.. confval:: extras=MULTI-LINE-LIST

    .. versionadded:: 2.4

    A list of "extras" to be installed with the sdist or develop install.
    For example, ``extras = testing`` is equivalent to ``[testing]`` in a
    ``pip install`` command.

.. confval:: description=SINGLE-LINE-TEXT

    A short description of the environment, this will be used to explain
    the environment to the user upon listing environments for the command
    line with any level of verbosity higher than zero. **default**: empty string

Substitutions
-------------

Any ``key=value`` setting in an ini-file can make use
of value substitution through the ``{...}`` string-substitution pattern.

You can escape curly braces with the ``\`` character if you need them, for example::

    commands = echo "\{posargs\}" = {posargs}

Globally available substitutions
++++++++++++++++++++++++++++++++

``{toxinidir}``
    the directory where tox.ini is located

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
    OS-specific path separator (``:`` os \*nix family, ``;`` on Windows). May be used in `setenv`,
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
and replace with and empty string if the environment variable does not
exist.

Substitutions can also be nested. In that case they are expanded starting
from the innermost expression::

    {env:KEY:{env:DEFAULT_OF_KEY}}

the above example is roughly equivalent to
``os.environ.get('KEY', os.environ['DEFAULT_OF_KEY'])``

.. _`command positional substitution`:
.. _`positional substitution`:

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

    Configuring :confval:`basepython` for environments using default factors
    will result in a warning. Configure :confval:`ignore_basepython_conflict`
    if you wish to explicitly ignore these conflicts, allowing you to define a
    global :confval:`basepython` for all environments *except* those with
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
        py34-mysql: PyMySQL     ; use if both py34 and mysql are in the env name
        py27,py36: urllib3      ; use if either py36 or py27 are in the env name
        py{27,36}-sqlite: mock  ; mocking sqlite in python 2.x & 3.6
        !py34-sqlite: mock      ; mocking sqlite, except in python 3.4
        sqlite-!py34: mock      ; (same as the line above)

Take a look at the first ``deps`` line. It shows how you can special case
something for a combination of factors, by just hyphenating the combining
factors together. This particular line states that ``PyMySQL`` will be loaded
for python 3.3, mysql environments, e.g. ``py34-django15-mysql`` and
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
For example:

.. code-block:: ini

    [tox]
    envlist = py27,py36,coverage

    [testenv]
    deps =
        flake8
        coverage: coverage

    [testenv:py27]
    deps =
        {{[testenv]deps}}
        pytest

With the previous configuration, it will install:

- ``flake8`` and ``pytest`` packages for ``py27`` environment.
- ``flake8`` package for ``py36`` environment.
- ``flake8`` and ``coverage`` packages for ``coverage`` environment.

Advanced settings
-----------------

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

Other Rules and notes
=====================

* ``path`` specifications: if a specified ``path`` is a relative path
  it will be considered as relative to the ``toxinidir``, the directory
  where the configuration file resides.

.. include:: links.rst
