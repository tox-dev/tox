tox-2.0: plugins, platform, env isolation
==========================================

tox-2.0 was released to pypi, a major new release with *mostly*
backward-compatible enhancements and fixes:

- experimental support for plugins, see https://testrun.org/tox/latest/plugins.html
  which includes also a refined internal registration mechanism for new testenv
  ini options.  You can now ask tox which testenv ini parameters exist
  with ``tox --help-ini``.

- ENV isolation: only pass through very few environment variables from the
  tox invocation to the test environments.  This may break test runs that
  previously worked with tox-1.9 -- you need to either use the
  ``setenv`` or ``passenv`` ini variables to set appropriate environment
  variables.

- PLATFORM support: you can set ``platform=REGEX`` in your testenv sections
  which lets tox skip the environment if the REGEX does not match ``sys.platform``.

- tox now stops execution of test commands if the first of them fails unless
  you set ``ignore_errors=True``.

Thanks to Volodymyr Vitvitski, Daniel Hahler, Marc Abramowitz, Anthon van
der Neuth and others for contributions.

More documentation about tox in general:

    http://tox.testrun.org/

Installation:

    pip install -U tox

code hosting and issue tracking on bitbucket:

    https://bitbucket.org/hpk42/tox

What is tox?
----------------

tox standardizes and automates tedious test activities driven from a
simple ``tox.ini`` file, including:

* creation and management of different virtualenv environments
  with different Python interpreters
* packaging and installing your package into each of them
* running your test tool of choice, be it nose, py.test or unittest2 or other tools such as "sphinx" doc checks
* testing dev packages against each other without needing to upload to PyPI

best,
Holger Krekel, merlinux GmbH

2.0.0
-----------

- (new) introduce environment variable isolation:
  tox now only passes the PATH and PIP_INDEX_URL variable from the tox
  invocation environment to the test environment and on Windows
  also ``SYSTEMROOT``, ``PATHEXT``, ``TEMP`` and ``TMP`` whereas
  on unix additionally ``TMPDIR`` is passed.  If you need to pass
  through further environment variables you can use the new ``passenv`` setting,
  a space-separated list of environment variable names.  Each name
  can make use of fnmatch-style glob patterns.  All environment
  variables which exist in the tox-invocation environment will be copied
  to the test environment.

- a new ``--help-ini`` option shows all possible testenv settings and
  their defaults.

- (new) introduce a way to specify on which platform a testenvironment is to
  execute: the new per-venv "platform" setting allows to specify
  a regular expression which is matched against sys.platform.
  If platform is set and doesn't match the platform spec in the test
  environment the test environment is ignored, no setup or tests are attempted.

- (new) add per-venv "ignore_errors" setting, which defaults to False.
   If ``True``, a non-zero exit code from one command will be ignored and
   further commands will be executed (which was the default behavior in tox <
   2.0).  If ``False`` (the default), then a non-zero exit code from one command
   will abort execution of commands for that environment.

- show and store in json the version dependency information for each venv

- remove the long-deprecated "distribute" option as it has no effect these days.

- fix issue233: avoid hanging with tox-setuptools integration example. Thanks simonb.

- fix issue120: allow substitution for the commands section.  Thanks
  Volodymyr Vitvitski.

- fix issue235: fix AttributeError with --installpkg.  Thanks
  Volodymyr Vitvitski.

- tox has now somewhat pep8 clean code, thanks to Volodymyr Vitvitski.

- fix issue240: allow to specify empty argument list without it being
  rewritten to ".".  Thanks Daniel Hahler.

- introduce experimental (not much documented yet) plugin system
  based on pytest's externalized "pluggy" system.
  See tox/hookspecs.py for the current hooks.

- introduce parser.add_testenv_attribute() to register an ini-variable
  for testenv sections.  Can be used from plugins through the
  tox_add_option hook.

- rename internal files -- tox offers no external API except for the
  experimental plugin hooks, use tox internals at your own risk.

- DEPRECATE distshare in documentation
