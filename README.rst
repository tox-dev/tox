|Latest version on PyPi| |Supported Python versions| |Azure Pipelines
build status| |Test Coverage| |Documentation status| |Code style: black|

.. raw:: html

    <a href="https://tox.readthedocs.io">
        <img src="https://raw.githubusercontent.com/tox-dev/tox/master/docs/_static/img/tox.png"
             alt="tox logo"
             height="150px"
             align="right">
    </a>

tox automation project
======================

**Command line driven CI frontend and development task automation tool**

At its core tox povides a convenient way to run arbitrary commands in
isolated environments to serve as a single entry point for build, test
and release activities.

tox is highly
`configurable <https://tox.readthedocs.io/en/latest/config.html>`__ and
`pluggable <https://tox.readthedocs.io/en/latest/plugins.html>`__.

A simple example
~~~~~~~~~~~~~~~~

tox is mainly used as a command line tool and needs a ``tox.ini`` or a
``tool.tox`` section in ``pyproject.toml`` containing the configuration.

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

**Note:** To learn more about what you can do with tox, have a look at `existing projects using tox <https://github.com/search?l=INI&q=tox.ini+in%3Apath&type=Code>`__.

How it works
------------

tox creates virtual environments for all configured so called
``testenvs``, it then installs the project and other necessary
dependencies and runs the configured set of commands. See `system
overview <https://tox.readthedocs.io/en/latest/#system-overview>`__
for more details.

.. raw:: html

    <a href="https://tox.readthedocs.io/en/latest/#system-overview">
        <img src="https://raw.githubusercontent.com/tox-dev/tox/master/docs/img/tox_flow.png"
             alt="tox flow"
             width="800px"
             align="center">
    </a>

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

Documentation
-------------

Documentation for tox can be found on `Read The Docs <https://tox.readthedocs.org>`__

Communication / questions
-------------------------

If you have questions about tox you can first check if they have already been answered or are already being discussed on our `issue tracker <https://github.com/tox-dev/tox/issues?utf8=%E2%9C%93&q=is%3Aissue+sort%3Aupdated-desc+label%3A%22type%3Aquestion+%3Agrey_question%3A%22+>`__ or questions tagged with ``tox`` on `Stack Overflow <https://stackoverflow.com/questions/tagged/tox>`__.

If you want to discuss topics or propose changes that might not (yet) fit into an issue, you can get in touch via mail through `tox-dev@python.org <mailto:tox-dev@python.org>`__.

We also have a `Gitter community <https://gitter.im/tox-dev/>`__.

Contributing
------------

Contributions are welcome. See
`contributing <https://github.com/tox-dev/tox/blob/master/CONTRIBUTING.rst>`__
and our `Contributor Covenant Code of
Conduct <https://github.com/tox-dev/tox/blob/master/CODE_OF_CONDUCT.md>`__.

Currently the `code <https://github.com/tox-dev/tox>`__  and the `issues <https://github.com/tox-dev/tox/issues>`__ are hosted on Github.

The project is licensed under `MIT <https://github.com/tox-dev/tox/blob/master/LICENSE>`__.

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
