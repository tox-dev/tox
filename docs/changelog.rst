Release History
===============

.. include:: _draft.rst

.. towncrier release notes start

v4.0.0a2 (2021-01-09)
---------------------

Features - 4.0.0a2
~~~~~~~~~~~~~~~~~~
- Add option to disable colored output, and support ``NO_COLOR`` and ``FORCE_COLOR`` environment variables - by
  :user:`gaborbernat`. (`#1630 <https://github.com/tox-dev/tox/issues/1630>`_)

Bugfixes - 4.0.0a2
~~~~~~~~~~~~~~~~~~
- Fix coverage generation in CI - by :user:`gaborbernat`. (`#1551 <https://github.com/tox-dev/tox/issues/1551>`_)
- Fix the CI failures:

  - drop Python 3.5 support as it's not expected to get to a release before EOL,
  - fix test using ``\n`` instead of ``os.linesep``,
  - Windows Python 3.6 does not contain ``_overlapped.ReadFileInto``

  - by :user:`gaborbernat`. (`#1556 <https://github.com/tox-dev/tox/issues/1556>`_)

Improved Documentation - 4.0.0a2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Add base documentation by merging virtualenv structure with tox 3 - by :user:`gaborbernat`. (`#1551 <https://github.com/tox-dev/tox/issues/1551>`_)


v4.0.0a1
--------
* First version all is brand new.

.. warning::

   The current tox is the second iteration of implementation. From version ``0.5`` all the way to ``3.X``
   we numbered the first iteration. Version ``4.0.0a1`` is a complete rewrite of the package, and as such this release
   history starts from there. The old changelog is still available in the
   `legacy branch documentation <https://tox.readthedocs.io/en/legacy/changelog.html>`_.
