tox 1.2: the virtualenv-based test run automatizer
===========================================================================

I am happy to announce tox 1.2, now using and depending on the latest
virtualenv code and containing some bug fixes.  TOX automates tedious
test activities driven from a simple ``tox.ini`` file, including:

* creation and management of different virtualenv environments with
  different Python interpreters
* packaging and installing your package into each of them
* running your test tool of choice, be it nose, py.test or unittest2 or
  other tools such as "sphinx" doc checks
* testing dev packages against each other without needing to upload to PyPI

It works well on virtually all Python interpreters that support virtualenv.

Docs and examples are at:

    http://tox.testrun.org/

Installation:

    pip install -U tox

code hosting and issue tracking on bitbucket:

    https://bitbucket.org/hpk42/tox

best,
Holger Krekel

1.2 compared to 1.1
---------------------

- remove the virtualenv.py that was distributed with tox and depend
  on virtualenv-1.6.4 (possible now since the latter fixes a few bugs
  that the inling tried to work around)
- fix issue10: work around UnicodeDecodeError when inokving pip (thanks
  Marc Abramowitz)
- fix a problem with parsing {posargs} in tox commands (spotted by goodwill)
- fix the warning check for commands to be installed in testevironment
  (thanks Michael Foord for reporting)
