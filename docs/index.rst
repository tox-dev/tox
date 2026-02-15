##########################
 tox - automation project
##########################

``tox`` aims to automate and standardize testing in Python. It is part of a larger vision of easing the packaging,
testing and release process of Python software (alongside `pytest <https://docs.pytest.org/en/latest/>`_ and `devpi
<https://www.devpi.net>`_).

.. image:: https://img.shields.io/pypi/v/tox?style=flat-square
    :target: https://pypi.org/project/tox/#history
    :alt: Latest version on PyPI

.. image:: https://img.shields.io/pypi/implementation/tox?style=flat-square
    :alt: PyPI - Implementation

.. image:: https://img.shields.io/pypi/pyversions/tox?style=flat-square
    :alt: PyPI - Python Version

.. image:: https://readthedocs.org/projects/tox/badge/?version=latest&style=flat-square
    :target: https://tox.wiki/en/latest/
    :alt: Documentation status

.. image:: https://img.shields.io/discord/802911963368783933?style=flat-square
    :target: https://discord.com/invite/tox
    :alt: Discord

.. image:: https://img.shields.io/pypi/dm/tox?style=flat-square
    :target: https://pypistats.org/packages/tox
    :alt: PyPI - Downloads

.. image:: https://img.shields.io/pypi/l/tox?style=flat-square
    :target: https://opensource.org/license/mit
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

- checking your package builds and installs correctly under different environments (such as different Python
  implementations, versions or installation dependencies),
- running your tests in each of the environments with the test tool of choice,
- acting as a frontend to continuous integration servers, greatly reducing boilerplate and merging CI and shell-based
  testing.

**************
 Useful links
**************

**Tutorials**

- `Oliver Bestwalter - Automating Build, Test and Release Workflows with tox
  <https://www.youtube.com/watch?v=PrAyvH-tm8E>`_
- `Bernat Gabor - Standardize Testing in Python <https://www.youtube.com/watch?v=SFqna5ilqig>`_

.. comment: split here

.. toctree::
    :hidden:

    installation
    getting_started
    user_guide
    howto
    config
    cli_interface
    plugins/index
    development
    changelog
