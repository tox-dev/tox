tox-1.9: refinements, fixes (+detox-0.9.4)
==========================================

tox-1.9 was released to pypi, a maintenance release with mostly
backward-compatible enhancements and fixes.  However, tox now defaults
to pip-installing only non-development releases and you have to set "pip_pre =
True" in your testenv section to have it install development ("pre") releases.

In addition, there is a new detox-0.9.4 out which allow to run tox test
environments in parallel and fixes a compat problem with eventlet.

Thanks to Alexander Schepanosvki, Florian Schulze and others for the
contributed fixes and improvements.

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


1.9.0
-----------

- fix issue193: Remove ``--pre`` from the default ``install_command``; by
  default tox will now only install final releases from PyPI for unpinned
  dependencies. Use ``pip_pre = true`` in a testenv or the ``--pre``
  command-line option to restore the previous behavior.

- fix issue199: fill resultlog structure ahead of virtualenv creation

- refine determination if we run from Jenkins, thanks Borge Lanes.

- echo output to stdout when ``--report-json`` is used

- fix issue11: add a ``skip_install`` per-testenv setting which
  prevents the installation of a package. Thanks Julian Krause.

- fix issue124: ignore command exit codes; when a command has a "-" prefix,
  tox will ignore the exit code of that command

- fix issue198: fix broken envlist settings, e.g. {py26,py27}{-lint,}

- fix issue191: lessen factor-use checks

