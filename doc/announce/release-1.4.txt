tox 1.4: the virtualenv-based test run automatizer
=============================================================================

I am happy to announce tox 1.4 which brings:

- improvements with configuration file syntax, now allowing re-using
  selected settings across config file sections. see http://testrun.org/tox/latest/config.html#substitution-for-values-from-other-sections

- terminal reporting was simplified and streamlined.  Now with
  verbosity==0 (the default), less information will be shown
  and you can use one or multiple "-v" options to increase verbosity.

- internal re-organisation so that the separately released "detox" 
  tool can reuse tox code to implement a fully distributed tox run. 

More documentation:

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
Holger Krekel


1.4
-----------------

- fix issue26 - no warnings on absolute or relative specified paths for commands
- fix issue33 - commentchars are ignored in key-value settings allowing
  for specifying commands like: python -c "import sys ; print sys"
  which would formerly raise irritating errors because the ";"
  was considered a comment
- tweak and improve reporting
- refactor reporting and virtualenv manipulation 
  to be more accessible from 3rd party tools
- support value substitution from other sections
  with the {[section]key} syntax
- fix issue29 - correctly point to pytest explanation
  for importing modules fully qualified
- fix issue32 - use --system-site-packages and don't pass --no-site-packages
- add python3.3 to the default env list, so early adopters can test
- drop python2.4 support (you can still have your tests run on
  python-2.4, just tox itself requires 2.5 or higher.
