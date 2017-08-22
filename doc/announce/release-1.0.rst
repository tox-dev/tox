tox 1.0: the rapid multi-python test automatizer
===========================================================================

I am happy to announce tox 1.0, mostly a stabilization and streamlined
release.  TOX automates tedious test activities driven from a 
simple ``tox.ini`` file, including:

* creation and management of different virtualenv environments with
  different Python interpreters
* packaging and installing your package into each of them
* running your test tool of choice, be it nose, py.test or unittest2 or
  other tools such as "sphinx" doc checks
* testing dev packages against each other without needing to upload to PyPI

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

- fix issue24: introduce a way to set environment variables for
  for test commands (thanks Chris Rose)
- fix issue22: require virtualenv-1.6.1, obsoleting virtualenv5 (thanks Jannis Leidel)
  and making things work with pypy-1.5 and python3 more seemlessly
- toxbootstrap.py (used by jenkins build slaves) now follows the latest release of virtualenv
- fix issue20: document format of URLs for specifying dependencies
- fix issue19: substitute Hudson for Jenkins everywhere following the renaming
  of the project.  NOTE: if you used the special [tox:hudson]
  section it will now need to be named [tox:jenkins].
- fix issue 23 / apply some ReST fixes
- change the positional argument specifier to use {posargs:} syntax and
  fix issues #15 and #10 by refining the argument parsing method (Chris Rose)
- remove use of inipkg lazy importing logic -
  the namespace/imports are anyway very small with tox.
- fix a fspath related assertion to work with debian installs which uses
  symlinks
- show path of the underlying virtualenv invocation and bootstrap
  virtualenv.py into a working subdir
- added a CONTRIBUTORS file
