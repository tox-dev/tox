:orphan:

#####
 tox
#####

************************************************
 virtualenv-based automation of test activities
************************************************

:Manual section: 1
:Manual group: User Commands

SYNOPSIS
========

**tox** [*options*] [*command* [*command-options*]]

DESCRIPTION
===========

tox aims to automate and standardize testing in Python. It is part of a larger vision of easing the packaging, testing
and release process of Python software.

tox creates virtual environments for multiple Python versions, installs project dependencies, and runs tests in each
environment. It supports parallel execution, custom test commands, and extensive configuration.

COMMANDS
========

**run** (*default*)
    Execute test environments. This is the default command if none is specified.

**list** (*or* **l**)
    List configured environments with their descriptions.

**config** (*or* **c**)
    Show tox configuration details for debugging and inspection.

**exec** (*or* **e**)
    Execute a command in a tox environment without running the full test suite.

**devenv** (*or* **d**)
    Create a development environment from a tox environment definition.

**legacy**
    Legacy tox 3.x compatibility mode for older configurations.

For command-specific help, use: **tox** *command* **--help**

OPTIONS
=======

For a complete list of options, run ``tox --help`` or see the online documentation at https://tox.wiki/

Common options:

**-h, --help**
    Show help message and exit.

**-v, --verbose**
    Increase verbosity (can be used multiple times).

**-q, --quiet**
    Decrease verbosity (can be used multiple times).

**-r, --recreate**
    Recreate the test environment.

**-e** *ENV*
    Run specific test environments (comma-separated).

**--conf** *FILE*
    Configuration file to use.

**--workdir** *DIR*
    tox working directory (default: .tox).

**--override** *KEY=VALUE*, **-x** *KEY=VALUE*
    Override a configuration value.

FILES
=====

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
=====================

``TOX_*``
    Any tox configuration setting can be overridden via environment variables with the ``TOX_`` prefix. For example,
    ``TOX_SKIP_ENV`` can override the ``skip_env`` setting.

**NO_COLOR**
    When set to any non-empty value, disables colored output.

**FORCE_COLOR**
    When set to any non-empty value, forces colored output even when stdout is not a terminal.

**TOX_PARALLEL_NO_SPINNER**
    When set, disables the progress spinner during parallel execution.

SEE ALSO
========

Full documentation: https://tox.wiki/

**pip**\(1), **pytest**\(1), **virtualenv**\(1)

AUTHOR
======

tox development team

https://github.com/tox-dev/tox

COPYRIGHT
=========

MIT License
