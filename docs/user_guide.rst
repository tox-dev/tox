User Guide
==========

Basic example
-----------------
Put basic information about your project and the test environments you want your project to run in into a ``tox.ini``
file residing at the root of your project:

.. code-block:: ini

    # content of: tox.ini at the root of the project
    [tox]
    envlist =
        py38
        py37

    [testenv]
    # install pytest in the virtualenv where commands will be executed
    deps =
        pytest >= 5, <6
    commands =
        # NOTE: you can run any command line tool here - not just tests
        pytest

You can also try generating a ``tox.ini`` file automatically, by running ``tox-quickstart`` and then answering a few
simple questions. To sdist-package, install and test your project against Python3.7 and Python3.8, just type:

.. code-block:: console

    tox

and watch things happening (you must have python3.7 and python3.8 installed in your environment otherwise you will see
errors). When you run ``tox`` a second time you'll note that it runs much faster because it keeps track of virtualenv
details and will not recreate or re-install dependencies.

System overview
---------------

.. figure:: img/tox_flow.png
   :align: center
   :width: 800px

   tox workflow diagram

tox roughly follows the following phases:

1. **configuration:** load ``tox.ini`` and merge it with options from the command line and the operating system
   environment variables.
2. **packaging** (optional): create a source distribution of the current project by invoking

   .. code-block:: bash

      python setup.py sdist

   Note that for this operation the same Python environment will be used as the one tox is installed into (therefore you
   need to make sure that it contains your build dependencies). Skip this step for application projects that don't have
   a ``setup.py``.

3. **environment** - for each tox environment (e.g. ``py37``, ``py38``) do:

   1. **environment creation**: create a fresh environment, by default :pypi:`virtualenv` is used. tox will
   automatically try to discover a valid Python interpreter version by using the environment name (e.g. ``py37`` means
   Python 3.7 and the ``basepython`` configuration value) and the current operating system ``PATH`` value. This is
   created at first run only to be re-used at subsequent runs. If certain aspects of the project change, a re-creation
   of the environment is automatically triggered. To force the recreation tox can be invoked with
   ``-r``/``--recreate``.

   2. **install** (optional): install the environment dependencies specified inside the ``deps`` configuration
   section, and then the earlier packaged source distribution. By default ``pip`` is used to install packages, however
   one can customise this via ``install_command``. Note ``pip`` will not update project dependencies (specified
   either in the ``install_requires`` or the ``extras`` section of the ``setup.py``) if any version already exists in
   the virtual environment; therefore we recommend to recreate your environments whenever your project dependencies
   change.

   3. **commands**: run the specified commands in the specified order. Whenever the exit code of any of them is not
   zero stop, and mark the environment failed. Note, starting a command with a single dash character means ignore exit
   code.

6. **report** print out a report of outcomes for each tox environment:

   .. code:: bash

      ____________________ summary ____________________
      py37: commands succeeded
      ERROR:   py38: commands failed

   Only if all environments ran successfully tox will return exit code ``0`` (success). In this case you'll also see the
   message ``congratulations :)``.

tox will take care of environment isolation for you: it will strip away all operating system environment variables not
specified via ``passenv``. Furthermore, it will also alter the ``PATH`` variable so that your commands resolve
within the current active tox environment. In general all executables in the path are available in ``commands``, but
tox will emit a warning if it was not explicitly allowed via ``whitelist_externals``.

Current features
----------------

* **automation of tedious Python related test activities**
* **test your Python package against many interpreter and dependency configs**

    - automatic customizable (re)creation of :pypi:`virtualenv` test environments - installs your ``setup.py`` based
      project into each virtual environment
    - test-tool agnostic: runs pytest, nose or unittests in a uniform manner

* ``plugin system`` to modify tox execution with simple hooks.
* uses :pypi:`pip` and :pypi:`setuptools` by default. Support for configuring the installer command through
  ``install_command``.
* **cross-Python compatible**: CPython-3.5 and higher, pypy 3.6+ and higher.
* **cross-platform**: Windows and Unix style environments
* **integrates with continuous integration servers** like Jenkins (formerly known as Hudson) and helps you to avoid
  boilerplatish and platform-specific build-step hacks.
* **full interoperability with devpi**: is integrated with and is used for testing in the :pypi:`devpi` system, a
  versatile PyPI index server and release managing tool.
* **driven by a simple ini-style config file**
* **documented** examples and configuration
* **concise reporting** about tool invocations and configuration errors
* **professionally** supported
* supports using different / multiple PyPI index servers
