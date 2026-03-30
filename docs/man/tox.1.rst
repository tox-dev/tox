:orphan:

===
tox
===

---------------------------------------------------
virtualenv-based automation of test activities
---------------------------------------------------

:Manual section: 1
:Manual group: User Commands

SYNOPSIS
--------

**tox** [*options*] [**run** | **run-parallel** | **depends** | **man** | **list** | **devenv** | **schema** | **config** | **quickstart** | **exec** | **legacy**] [*command-options*]

DESCRIPTION
-----------

tox aims to automate and standardize testing in Python.
It is part of a larger vision of easing the packaging,
testing and release process of Python software.

tox creates virtual environments for multiple Python versions,
installs project dependencies, and runs tests in each environment.
It supports parallel execution, custom test commands, and extensive configuration.

COMMANDS
--------

**run** (*or* **r**)
    run environments

**run-parallel** (*or* **p**)
    run environments in parallel

**depends** (*or* **de**)
    visualize tox environment dependencies

**man**
    Set up tox man page for current shell

**list** (*or* **l**)
    list environments

**devenv** (*or* **d**)
    sets up a development environment at ENVDIR based on the tox configuration specified 

**schema**
    Generate schema for tox configuration

**config** (*or* **c**)
    show tox configuration

**quickstart** (*or* **q**)
    Command line script to quickly create a tox config file for a Python project

**exec** (*or* **e**)
    execute an arbitrary command within a tox environment

**legacy** (*or* **le**)
    legacy entry-point command

For command-specific help, use: **tox** *command* **--help**

OPTIONS
-------

**-h**, **--help**
    show this help message and exit

**--colored**
    should output be enriched with colors, default is yes unless TERM=dumb or NO_COLOR is defined.

**--stderr-color**
    color for stderr output, use RESET for terminal defaults.

**-v**, **--verbose**
    increase verbosity

**-q**, **--quiet**
    decrease verbosity

**--exit-and-dump-after** *seconds*
    dump tox threads after n seconds and exit the app - useful to debug when tox hangs, 0 means disabled

**-c**, **--conf** *file*
    configuration file/folder for tox (if not specified will discover one)

**--workdir** *dir*
    tox working directory (if not specified will be the folder of the config file)

**--root** *dir*
    project root directory (if not specified will be the folder of the config file)

**--runner**
    the tox run engine to use when not explicitly stated in tox env configuration

**--version**
    show program's and plugins version number and exit

**--no-provision** *REQ_JSON*
    do not perform provision, but fail and if a path was provided write provision metadata as JSON to it

**--no-recreate-provision**
    if recreate is set do not recreate provision tox environment

**-r**, **--recreate**
    recreate the tox environments

**-x**, **--override**
    configuration override(s), e.g., -x testenv:pypy3.ignore_errors=True

FILES
-----

**tox.toml**
    Primary configuration file in TOML format (recommended).

**tox.ini**
    Configuration file in INI format.

**pyproject.toml**
    Alternative configuration location under the ``[tool.tox]`` section.

**setup.cfg**
    Legacy configuration location (deprecated).

The configuration files are searched in the order listed above. The first file found is used.

ENVIRONMENT VARIABLES
---------------------

``TOX_*``
    Any tox configuration setting can be overridden via environment variables with the ``TOX_`` prefix.

**NO_COLOR**
    When set to any non-empty value, disables colored output.

**FORCE_COLOR**
    When set to any non-empty value, forces colored output even when stdout is not a terminal.

**TOX_PARALLEL_NO_SPINNER**
    When set, disables the progress spinner during parallel execution.

SEE ALSO
--------

Full documentation: https://tox.wiki/

**pip**\(1), **pytest**\(1), **virtualenv**\(1)

AUTHOR
------

tox development team

https://github.com/tox-dev/tox
