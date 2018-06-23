Welcome to the tox automation project
===============================================

vision: standardize testing in Python
---------------------------------------------

``tox`` aims to automate and standardize testing in Python.  It is part
of a larger vision of easing the packaging, testing and release process
of Python software.

What is tox?
--------------------

tox is a generic virtualenv_ management and test command line tool you can use for:

* checking your package installs correctly with different Python versions and
  interpreters

* running your tests in each of the environments, configuring your test tool of choice

* acting as a frontend to Continuous Integration servers, greatly
  reducing boilerplate and merging CI and shell-based testing.


Basic example
-----------------

First, install ``tox`` with ``pip install tox``.
Then put basic information about your project and the test environments you
want your project to run in into a ``tox.ini`` file residing
right next to your ``setup.py`` file:

.. code-block:: ini

    # content of: tox.ini , put in same dir as setup.py
    [tox]
    envlist = py27,py36

    [testenv]
    deps = pytest       # install pytest in the virtualenv where commands will be executed
    commands =
        # whatever extra steps before testing might be necessary
        pytest          # or any other test runner that you might use

You can also try generating a ``tox.ini`` file automatically, by running
``tox-quickstart`` and then answering a few simple questions.

To sdist-package, install and test your project against Python2.7 and Python3.6, just type::

    tox

and watch things happening (you must have python2.7 and python3.6 installed in your
environment otherwise you will see errors).  When you run ``tox`` a second time
you'll note that it runs much faster because it keeps track of virtualenv details
and will not recreate or re-install dependencies.  You also might want to
checkout :doc:`examples` to get some more ideas.

Current features
-------------------

* **automation of tedious Python related test activities**

* **test your Python package against many interpreter and dependency configs**

    - automatic customizable (re)creation of virtualenv_ test environments

    - installs your ``setup.py`` based project into each virtual environment

    - test-tool agnostic: runs pytest, nose or unittests in a uniform manner

* :doc:`plugin system <plugins>` to modify tox execution with simple hooks.

* uses pip_ and setuptools_ by default.  Support for configuring the installer command
  through :confval:`install_command=ARGV`.

* **cross-Python compatible**: CPython-2.7, 3.4 and higher, Jython and pypy_.

* **cross-platform**: Windows and Unix style environments

* **integrates with continuous integration servers** like Jenkins_
  (formerly known as Hudson) and helps you to avoid boilerplatish
  and platform-specific build-step hacks.

* **full interoperability with devpi**: is integrated with and
  is used for testing in the devpi_ system, a versatile pypi
  index server and release managing tool.

* **driven by a simple ini-style config file**

* **documented** :doc:`examples <examples>` and :doc:`configuration <config>`

* **concise reporting** about tool invocations and configuration errors

* **professionally** :doc:`supported <support>`

* supports :ref:`using different / multiple PyPI index servers  <multiindex>`


.. toctree::
   :hidden:

   install
   examples
   config
   support
   changelog
   plugins
   developers
   example/result
   announce/changelog-only


.. include:: links.rst
