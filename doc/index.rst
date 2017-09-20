============================
tox - testing out of the box
============================

**Welcome to the tox automation project - helping to standardize testing in Python since 2012**

What is tox?
============

``tox`` aims to automate and standardize testing and task automation in Python.  It is part of a larger vision to be unifying frontend between CI systems and local development activity therfore easing the packaging, testing and release process.


Most typical usages are:

* Build your package and check if it installs correctly with different Python versions and interpreters

* Run your tests in each of the environments, configuring your test tool of choice

* Build and deploy the documentation of the project

In a nutshell
-------------

**Supported Pythons**: CPython 2.6-3.6, jython, pypy

**Supported operating systems**: Linux, Windows, macOS, Unix

**License**: MIT

**development**: https://github.com/tox-dev

Installation
============

.. code-block:: shell

   pip install tox

It is fine to install ``tox`` itself into a virtualenv_ environment.

Basic example
=============

First, install ``tox`` with ``pip install tox``.
Then put basic information about your project and the test environments you
want your project to run in into a ``tox.ini`` file residing
right next to your ``setup.py`` file::

    # content of: tox.ini , put in same dir as setup.py
    [tox]
    envlist = py26,py27
    [testenv]
    deps=pytest       # install pytest in the venvs
    commands=pytest  # or 'nosetests' or ...

You can also try generating a ``tox.ini`` file automatically, by running
``tox-quickstart`` and then answering a few simple questions.

To sdist-package, install and test your project against Python2.6 and Python2.7, just type::

    tox

... and watch things happening (you must have python2.6 and python2.7 installed in your
environment otherwise you will see errors).  When you run ``tox`` a second time
you'll note that it runs much faster because it keeps track of virtualenv details
and will not recreate or re-install dependencies.  You also might want to
checkout the :doc:`examples` to get some more ideas.

Current features
================

* **automation of tedious Python related test activities**

* **test your Python package against many interpreter and dependency configs**

    - automatic customizable (re)creation of virtualenv_ test environments

    - installs your ``setup.py`` based project into each virtual environment

    - test-tool agnostic: runs pytest, nose or unittests in a uniform manner

* :doc:`plugin system <plugins>` to modify tox execution with simple hooks.

* uses pip_ and setuptools_ by default.  Support for configuring the installer command
  through :confval:`install_command=ARGV`.

* **cross-Python compatible**: CPython-2.6, 2.7, 3.2 and higher, Jython and pypy_.

* **cross-platform**: Windows and Unix style environments

* **integrates with continuous integration servers** like Jenkins_ and helps you to avoid
  boilerplatish and platform-specific build-step hacks.

* **full interoperability with devpi**: is integrated with and is used for testing in the
  devpi_ system, a versatile pypi index server and release managing tool.

* **driven by a simple ini-style config file**

* **documented** :doc:`examples <examples>` and :doc:`configuration <config>`

* **concise reporting** about tool invocations and configuration errors

* **professionally** :ref:`support`

* supports :ref:`using different / multiple PyPI index servers  <multiindex>`

.. toctree::

    examples
    config
    config-advanced
    plugins
    developer-faq
    org

.. include:: ../CHANGELOG.rst

.. include:: ../CONTRIBUTING.rst

.. include:: _shared-links.rst
