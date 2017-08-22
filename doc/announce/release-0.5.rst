tox 0.5: a generic virtualenv and test management tool for Python
===========================================================================

I have been talking about with various people in the last year and
am happy to now announce the first release of ``tox``.  It aims
to automate tedious Python related test activities driven
from a simple ``tox.ini`` file, including:

* creation and management of different virtualenv environments
* installing your package into each of them
* running your test tool of choice (including e.g. running sphinx checks)
* testing packages against each other without needing to upload to PyPI

``tox`` runs well on Python2.4 up until Python3.1 and integrates
well with Continuous Integration servers Jenkins. There are many
real-life examples and a good chunk of docs.  Read it up on

    http://codespeak.net/tox

and please report any issues.  This is a fresh project and
i'd like to drive further improvements from real world needs.

best,

holger krekel

