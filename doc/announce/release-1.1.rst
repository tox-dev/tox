tox 1.1: the rapid multi-python test automatizer
===========================================================================

I am happy to announce tox 1.1, a bug fix release easing some commong
workflows.  TOX automates tedious test activities driven from a simple
``tox.ini`` file, including:

* creation and management of different virtualenv environments with
  different Python interpreters
* packaging and installing your package into each of them
* running your test tool of choice, be it nose, py.test or unittest2 or
  other tools such as "sphinx" doc checks
* testing dev packages against each other without needing to upload to PyPI

It works well on virtually all Python interpreters that support virtualenv.

Docs and examples are at:

    http://tox.readthedocs.org

Installation:

    pip install -U tox

Note that code hosting and issue tracking has moved from Google to Bitbucket:

    https://bitbucket.org/hpk42/tox

The 1.0 release includes contributions and is based on feedback and
work from Chris Rose, Ronny Pfannschmidt, Jannis Leidel, Jakob Kaplan-Moss,
Sridhar Ratnakumar, Carl Meyer and others.  Many thanks!

best,
Holger Krekel

CHANGES
---------------------

- fix issue5 - don't require argparse for python versions that have it
- fix issue6 - recreate virtualenv if installing dependencies failed
- fix issue3 - fix example on frontpage
- fix issue2 - warn if a test command does not come from the test
  environment
- fixed/enhanced: except for initial install always call "-U
  --no-deps" for installing the sdist package to ensure that a package
  gets upgraded even if its version number did not change. (reported on
  TIP mailing list and IRC)
- inline virtualenv.py (1.6.1) script to avoid a number of issues, 
  particularly failing to install python3 environents from a python2 
  virtualenv installation.
