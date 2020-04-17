tox - automation project
========================

``tox`` aims to automate and standardize testing in Python. It is part of a larger vision of easing the packaging,
testing and release process of Python software (alongside `pytest <https://docs.pytest.org/en/latest/>`_
and `devpi <https://devpi.net/>`_).

.. image:: https://img.shields.io/pypi/v/tox?style=flat-square
  :target: https://pypi.org/project/tox/#history
  :alt: Latest version on PyPI
.. image:: https://img.shields.io/pypi/implementation/tox?style=flat-square
  :alt: PyPI - Implementation
.. image:: https://img.shields.io/pypi/pyversions/tox?style=flat-square
  :alt: PyPI - Python Version
.. image:: https://readthedocs.org/projects/tox/badge/?version=latest&style=flat-square
  :target: https://tox.tox-dev.io
  :alt: Documentation status
.. image:: https://img.shields.io/gitter/room/tox-dev/tox?color=FF004F&style=flat-square
  :target: https://gitter.im/tox-dev/Lobby
  :alt: Gitter
.. image:: https://img.shields.io/pypi/dm/tox?style=flat-square
  :target: https://pypistats.org/packages/tox
  :alt: PyPI - Downloads
.. image:: https://img.shields.io/pypi/l/tox?style=flat-square
  :target: https://opensource.org/licenses/MIT
  :alt: PyPI - License
.. image:: https://img.shields.io/github/issues/tox-dev/tox?style=flat-square
  :target: https://github.com/tox-dev/tox/issues
  :alt: Open issues
.. image:: https://img.shields.io/github/issues-pr/tox-dev/tox?style=flat-square
  :target: https://github.com/tox-dev/tox/pulls
  :alt: Open pull requests
.. image:: https://img.shields.io/github/stars/tox-dev/tox?style=flat-square
  :target: https://pypistats.org/packages/tox
  :alt: Package popularity

tox is a generic virtual environment management and test command line tool you can use for:

* checking your package builds and installs correctly under different environments (such as different Python
  implementations, versions or install dependencies),
* running your tests in each of the environments with the test tool of choice,
* acting as a frontend to Continuous Integration servers, greatly reducing boilerplate and merging CI and
  shell-based testing.

Useful links
------------

**Related projects**

tox has influenced several other projects in the Python test automation space. If tox doesn't quite fit your needs or
you want to do more research, we recommend taking a look at these projects:

- `Invoke <https://www.pyinvoke.org/>`_ is a general-purpose task execution library, similar to Make. Invoke is far more
  general-purpose than tox but it does not contain the Python testing-specific features that tox specializes in.

- `Nox <https://nox.thea.codes>`_  is a project similar in spirit to tox but different in approach. Nox's key
  difference is that it uses Python scripts instead of a configuration file. Nox might be useful if you find tox's
  configuration too limiting but aren't looking to move to something as general-purpose as Invoke or Make.

**Tutorials**

* `Oliver Bestwalter - Automating Build, Test and Release Workflows with tox <https://www.youtube.com/watch?v=N5vscPTWKOk>`_
* `Bernat Gabor - Standardize Testing in Python <https://www.youtube.com/watch?v=SFqna5ilqig>`_

.. comment: split here

.. toctree::
   :hidden:

   installation
   user_guide
   cli_interface
   extend
   development
   changelog
