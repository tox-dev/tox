tox
===========

SYNOPSIS
--------

.. code-block::

    usage: tox [--version] [-h] [--help-ini] [-v] [-q] [--showconfig] [-l] [-a] [-c CONFIGFILE] [-e envlist] [--devenv ENVDIR] [--notest] [--sdistonly] [--skip-pkg-install] [-p [VAL]] [-o]
           [--parallel--safe-build] [--installpkg PATH] [--develop] [-i URL] [--pre] [-r] [--result-json PATH] [--discover PATH [PATH ...]] [--hashseed SEED] [--force-dep REQ]
           [--sitepackages] [--alwayscopy] [--no-provision [REQUIRES_JSON]] [-s [val]] [--workdir PATH]
           [args [args ...]]

    tox -h/--help

DESCRIPTION
-----------

``tox`` is a generic virtualenv management and test command line tool you can use for:

* checking that your package installs correctly with different Python versions and
  interpreters

* running your tests in each of the environments, configuring your test tool of choice

* acting as a frontend to Continuous Integration servers, greatly
  reducing boilerplate and merging CI and shell-based testing.


OPTIONS
-------

.. code-block::

    positional arguments:
      args                             additional arguments available to command positional substitution (default: None)

    optional arguments:
      --version                        report version information to stdout. (default: False)
      -h, --help                       show help about options (default: False)
      --help-ini, --hi                 show help about ini-names (default: False)
      -v, --verbose                    increase verbosity of reporting output.-vv mode turns off output redirection for package installation, above level two verbosity flags are passed through
                                       to pip (with two less level) (default: 0)
      -q, --quiet                      progressively silence reporting output. (default: 0)
      --showconfig                     show live configuration (by default all env, with -l only default targets, specific via TOXENV/-e) (default: False)
      -l, --listenvs                   show list of test environments (with description if verbose) (default: False)
      -a, --listenvs-all               show list of all defined environments (with description if verbose) (default: False)
      -c CONFIGFILE                    config file name or directory with 'tox.ini' file. (default: None)
      -e envlist                       work against specified environments (ALL selects all). (default: None)
      --devenv ENVDIR                  sets up a development environment at ENVDIR based on the env's tox configuration specified by `-e` (-e defaults to py). (default: None)
      --notest                         skip invoking test commands. (default: False)
      --sdistonly                      only perform the sdist packaging activity. (default: False)
      --skip-pkg-install               skip package installation for this run (default: False)
      -p [VAL], --parallel [VAL]       run tox environments in parallel, the argument controls limit: all, auto or missing argument - cpu count, some positive number, 0 to turn off (default: 0)
      -o, --parallel-live              connect to stdout while running environments (default: False)
      --parallel--safe-build           (deprecated) ensure two tox builds can run in parallel (uses a lock file in the tox workdir with .lock extension) (default: False)
      --installpkg PATH                use specified package for installation into venv, instead of creating an sdist. (default: None)
      --develop                        install package in the venv using 'setup.py develop' via 'pip -e .' (default: False)
      -i URL, --index-url URL          set indexserver url (if URL is of form name=url set the url for the 'name' indexserver, specifically) (default: None)
      --pre                            install pre-releases and development versions of dependencies. This will pass the --pre option to install_command (pip by default). (default: False)
      -r, --recreate                   force recreation of virtual environments (default: False)
      --result-json PATH               write a json file with detailed information about all commands and results involved. (default: None)
      --discover PATH [PATH ...]       for python discovery first try the python executables under these paths (default: [])
      --hashseed SEED                  set PYTHONHASHSEED to SEED before running commands. Defaults to a random integer in the range [1, 4294967295] ([1, 1024] on Windows). Passing 'noset'
                                       suppresses this behavior. (default: None)
      --force-dep REQ                  Forces a certain version of one of the dependencies when configuring the virtual environment. REQ Examples 'pytest<2.7' or 'django>=1.6'. (default: None)
      --sitepackages                   override sitepackages setting to True in all envs (default: False)
      --alwayscopy                     override alwayscopy setting to True in all envs (default: False)
      --no-provision [REQUIRES_JSON]   do not perform provision, but fail and if a path was provided write provision metadata as JSON to it (default: False)
      -s [val], --skip-missing-interpreters [val]
                                       don't fail tests for missing interpreters: {config,true,false} choice (default: config)
      --workdir PATH                   tox working directory (default: None)


ENVIRONMENT VARIABLES
---------------------

.. code-block::

    TOXENV: comma separated list of environments (overridable by '-e')
    TOX_SKIP_ENV: regular expression to filter down from running tox environments
    TOX_TESTENV_PASSENV: space-separated list of extra environment variables to be passed into test command environments
    PY_COLORS: 0 disable colorized output, 1 enable (default)
    TOX_PARALLEL_NO_SPINNER: 1 disable spinner for CI, 0 enable (default)
