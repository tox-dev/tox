|Latest version on PyPi| |Supported Python versions| |Azure Pipelines
build status| |Test Coverage| |Documentation status| |Code style: black|

.. image:: docs/_static/img/tox.png
   :target: https://tox.readthedocs.io
   :height: 150
   :alt: tox logo
   :align: right

tox automation project
======================

**Command line driven CI frontend and development task automation tool**

At its core tox povides a convenient way to run arbitrary commands in
isolated environments to serve as a single entry point for build, test
and release activities.

tox is highly
`configurable <https://tox.readthedocs.io/en/latest/config.html>`__ and
`pluggable <https://tox.readthedocs.io/en/latest/plugins.html>`__.

How it works
------------

tox creates virtual environments for all configured so called
``testenvs``, it then installs the project and other necessary
dependencies and runs the configured set of commands.

.. figure:: docs/img/tox_flow.png
   :alt: tox flow

   tox flow

See `system
overview <https://tox.readthedocs.io/en/latest/#system-overview>`__ for
more details.

tox can be used for …
---------------------

-  creating development environments
-  running static code analysis and test tools
-  automating package builds
-  running tests against the package build by tox
-  checking that packages install correctly with different Python
   versions/interpreters
-  unifying Continuous Integration and command line based testing
-  building and deploying project documentation
-  releasing a package to PyPI or any other platform
-  limit: your imagination

Usage
-----

tox is mainly used as a command line tool and needs a ``tox.ini`` or a
``tool.tox`` section in ``pyproject.toml`` containing the configuration.

A simple example
~~~~~~~~~~~~~~~~

To test a simple project that has some tests, here is an example with
the ``tox.ini`` in the root of the project:

.. code:: ini

   [tox]
   envlist = py27,py37

   [testenv]
   deps = pytest
   commands = pytest

.. code:: console

   $ tox

   [lots of output from what tox does]
   [lots of output from commands that were run]

   __________________ summary _________________
     py27: commands succeeded
     py37: commands succeeded
     congratulations :)

tox created two ``testenvs`` - one based on Python2.7 and one based on
Python3.7, it installed pytest in them and ran the tests. The report at
the end summarizes which ``testenvs`` have failed and which have
succeeded.

--------------

Contributions are welcome. See
`contributing <https://github.com/tox-dev/tox/blob/master/CONTRIBUTING.rst>`__
and our `Contributor Covenant Code of
Conduct <https://github.com/tox-dev/tox/blob/master/CODE_OF_CONDUCT.md>`__.

-  `docs are here <https://tox.readthedocs.org>`__
-  `code is here <https://github.com/tox-dev/tox>`__
-  `issue tracker is here <https://github.com/tox-dev/tox/issues>`__
-  `license is
   MIT <https://github.com/tox-dev/tox/blob/master/LICENSE>`__

.. |Latest version on PyPi| image:: https://badge.fury.io/py/tox.svg
   :target: https://badge.fury.io/py/tox
.. |Supported Python versions| image:: https://img.shields.io/pypi/pyversions/tox.svg
   :target: https://pypi.org/project/tox/
.. |Azure Pipelines build status| image:: https://dev.azure.com/toxdev/tox/_apis/build/status/tox%20ci?branchName=master
   :target: https://dev.azure.com/toxdev/tox/_build/latest?definitionId=9&branchName=master
.. |Test Coverage| image:: https://api.codeclimate.com/v1/badges/425c19ab2169a35e1c16/test_coverage
   :target: https://codeclimate.com/github/tox-dev/tox/code?sort=test_coverage
.. |Documentation status| image:: https://readthedocs.org/projects/tox/badge/?version=latest&style=flat-square
   :target: https://tox.readthedocs.io/en/latest/?badge=latest
.. |Code style: black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black
