#####
 tox
#####

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

******************
 Quick navigation
******************

**Tutorial** - Learn by doing

- :doc:`tutorial/getting-started` — Create your first tox environment and learn the basic workflow

**How-to guides** - Solve specific problems

- :doc:`how-to/install` — Install tox on your system
- :doc:`how-to/usage` — Common tasks and workflows with tox

**Reference** - Technical information

- :doc:`reference/config` — Complete configuration reference
- :doc:`reference/cli` — Command line interface options

**Explanation** - Understand the concepts

- :doc:`explanation` — How tox works, architecture, and design principles

**Extensions**

- :doc:`plugin/index` — Extend tox with custom plugins

***************
 Presentations
***************

Learn more about tox from maintainer presentations:

- `Oliver Bestwalter - Automating Build, Test and Release Workflows with tox
  <https://www.youtube.com/watch?v=PrAyvH-tm8E>`_
- `Bernat Gabor - Standardize Testing in Python <https://www.youtube.com/watch?v=SFqna5ilqig>`_

.. toctree::
    :hidden:
    :caption: Tutorial

    tutorial/getting-started

.. toctree::
    :hidden:
    :caption: How-to guides

    how-to/install
    how-to/usage

.. toctree::
    :hidden:
    :caption: Reference

    reference/config
    reference/cli

.. toctree::
    :hidden:
    :caption: Explanation

    explanation

.. toctree::
    :hidden:
    :caption: Extend

    plugin/index

.. toctree::
    :hidden:
    :caption: Project

    development
    changelog
