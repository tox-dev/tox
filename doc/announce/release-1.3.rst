tox 1.3: the virtualenv-based test run automatizer
===========================================================================

I am happy to announce tox 1.3, containing a few improvements
over 1.2.  TOX automates tedious test activities driven from a 
simple ``tox.ini`` file, including:

* creation and management of different virtualenv environments 
  with different Python interpreters
* packaging and installing your package into each of them
* running your test tool of choice, be it nose, py.test or unittest2 or other tools such as "sphinx" doc checks
* testing dev packages against each other without needing to upload to PyPI

Docs and examples are at:

    http://tox.testrun.org/

Installation:

    pip install -U tox

code hosting and issue tracking on bitbucket:

    https://bitbucket.org/hpk42/tox

best,
Holger Krekel

1.3
-----------------

- fix: allow to specify wildcard filesystem paths when 
  specifiying dependencies such that tox searches for 
  the highest version

- fix issue issue21: clear PIP_REQUIRES_VIRTUALENV which avoids
  pip installing to the wrong environment, thanks to bb's streeter

- make the install step honour a testenv's setenv setting
  (thanks Ralf Schmitt)

