tox 1.8: Generative/combinatorial environments specs
=============================================================================

I am happy to announce tox 1.8 which implements parametrized environments.

See https://tox.testrun.org/latest/config.html#generating-environments-conditional-settings
for examples and the new backward compatible syntax in your tox.ini file.

Many thanks to Alexander Schepanovski for implementing and refining
it based on the specifcation draft.

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


Changes 1.8 (compared to 1.7.2)
---------------------------------------

- new multi-dimensional configuration support.  Many thanks to
  Alexander Schepanovski for the complete PR with docs.
  And to Mike Bayer and others for testing and feedback.

- fix issue148: remove "__PYVENV_LAUNCHER__" from os.environ when starting
  subprocesses. Thanks Steven Myint.

- fix issue152: set VIRTUAL_ENV when running test commands,
  thanks Florian Ludwig.

- better report if we can't get version_info from an interpreter
  executable. Thanks Floris Bruynooghe.
