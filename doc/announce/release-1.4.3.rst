tox 1.4.3: the Python virtualenv-based testing automatizer
=============================================================================

tox 1.4.3 fixes some bugs and introduces a new script and two new options:

- "tox-quickstart" - run this script, answer a few questions, and
  get a tox.ini created for you (thanks Marc Abramowitz)

- "tox -l" lists configured environment names (thanks Lukasz Balcerzak)

- (experimental) "--installpkg=localpath" option which will skip the
  sdist-creation of a package and instead install the given localpath package.

- use pip-script.py instead of pip.exe on win32 to avoid windows locking
  the .exe

Note that the sister project "detox" should continue to work - it's a 
separately released project which drives tox test runs on multiple CPUs
in parallel.

More documentation:

    http://tox.testrun.org/

Installation:

    pip install -U tox

repository hosting and issue tracking on bitbucket:

    https://bitbucket.org/hpk42/tox


What is tox?
----------------

tox standardizes and automates tedious python driven test activities
driven from a simple ``tox.ini`` file, including:

* creation and management of different virtualenv environments 
  with different Python interpreters
* packaging and installing your package into each of them
* running your test tool of choice, be it nose, py.test or unittest2 or other tools such as "sphinx" doc checks
* testing dev packages against each other without needing to upload to PyPI

best,
Holger Krekel


CHANGELOG
================

1.4.3 (compared to 1.4.2)
--------------------------------

- introduce -l|--listenv option to list configured environments
  (thanks  Lukasz Balcerzak)

- fix downloadcache determination to work according to docs: Only
  make pip use a download cache if PIP_DOWNLOAD_CACHE or a 
  downloadcache=PATH testenv setting is present. (The ENV setting
  takes precedence)

- fix issue84 - pypy on windows creates a bin not a scripts venv directory
  (thanks Lukasz Balcerzak)

- experimentally introduce --installpkg=PATH option to install a package rather than
  create/install an sdist package.  This will still require and use
  tox.ini and tests from the current working dir (and not from the remote
  package).

- substitute {envsitepackagesdir} with the package installation directory (closes #72)
  (thanks g2p)

- issue #70 remove PYTHONDONTWRITEBYTECODE workaround now that
  virtualenv behaves properly (thanks g2p)

- merged tox-quickstart command, contributed by Marc Abramowitz, which
  generates a default tox.ini after asking a few questions

- fix #48 - win32 detection of pypy and other interpreters that are on PATH
  (thanks Gustavo Picon)

- fix grouping of index servers, it is now done by name instead of 
  indexserver url, allowing to use it to separate dependencies
  into groups even if using the same default indexserver.

- look for "tox.ini" files in parent dirs of current dir (closes #34)

- the "py" environment now by default uses the current interpreter
  (sys.executable) make tox' own setup.py test execute tests with it
  (closes #46)

- change tests to not rely on os.path.expanduser (closes #60),
  also make mock session return args[1:] for more precise checking (closes #61)
  thanks to Barry Warszaw for both.

