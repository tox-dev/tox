.. _getting_started:

#################
 Getting Started
#################

This tutorial walks you through creating your first tox project from scratch. By the end, you will have a working tox
configuration that runs tests and linting across multiple Python versions.

***************
 Prerequisites
***************

Before starting, make sure you have:

- Python 3.10 or later installed
- tox installed (see :doc:`installation`)
- A Python project you want to test (or follow along to create one)

Verify tox is available:

.. code-block:: bash

    tox --version

***********************************
 Creating your first configuration
***********************************

tox needs a configuration file where you define what tools to run and how to set up environments for them. tox supports
two configuration formats: TOML and INI. **TOML is the recommended format for new projects** -- it is more robust, has
proper type support, and avoids ambiguities inherent in INI parsing. INI remains supported for existing projects.

Create a ``tox.toml`` (or ``tox.ini``) at the root of your project:

.. tab:: TOML

    .. code-block:: toml

         env_list = ["3.13", "3.12", "lint"]

         [env_run_base]
         description = "run the test suite with pytest"
         deps = [
             "pytest>=8",
         ]
         commands = [["pytest", { replace = "posargs", default = ["tests"], extend = true }]]

         [env.lint]
         description = "run linters"
         skip_install = true
         deps = ["ruff"]
         commands = [["ruff", "check", { replace = "posargs", default = ["."], extend = true }]]

.. tab:: INI

    .. code-block:: ini

         [tox]
         env_list = 3.13, 3.12, lint

         [testenv]
         description = run the test suite with pytest
         deps =
             pytest>=8
         commands =
             pytest {posargs:tests}

         [testenv:lint]
         description = run linters
         skip_install = true
         deps =
             ruff
         commands = ruff check {posargs:.}

.. tip::

    You can also generate a ``tox.ini`` file automatically by running ``tox quickstart`` and answering a few questions.

*********************************
 Understanding the configuration
*********************************

The configuration has two parts: **core settings** and **environment settings**.

Core settings
=============

Core settings affect all environments or configure how tox itself behaves. They live at the root level in ``tox.toml``
(or under the ``[tox]`` section in ``tox.ini``).

.. tab:: TOML

    .. code-block:: toml

       env_list = ["3.13", "3.12", "lint"]

.. tab:: INI

    .. code-block:: ini

       [tox]
       env_list = 3.13, 3.12, lint

The :ref:`env_list` setting defines which environments run by default when you invoke ``tox`` without specifying any.
For the full list of core options, see :ref:`conf-core`.

Environment settings
====================

Each tox environment has its own configuration. Settings defined at the base level (``env_run_base`` in TOML,
``testenv`` in INI) are inherited by all environments unless overridden. Individual environments are configured under
``env.<name>`` in TOML or ``testenv:<name>`` in INI.

.. tab:: TOML

    .. code-block:: toml

         [env_run_base]
         description = "run the test suite with pytest"
         deps = ["pytest>=8"]
         commands = [["pytest", { replace = "posargs", default = ["tests"], extend = true }]]

         [env.lint]
         description = "run linters"
         skip_install = true
         deps = ["ruff"]
         commands = [["ruff", "check", "."]]

.. tab:: INI

    .. code-block:: ini

         [testenv]
         description = run the test suite with pytest
         deps =
             pytest>=8
         commands =
             pytest {posargs:tests}

         [testenv:lint]
         description = run linters
         skip_install = true
         deps =
             ruff
         commands = ruff check .

Here the ``lint`` environment overrides the base settings entirely, while ``3.13`` and ``3.12`` inherit from the base.

Environment names and Python versions
=====================================

Environment names can consist of alphanumeric characters, dashes, and dots. Names are split on dashes into **factors**
-- for example ``py311-django42`` splits into factors ``py311`` and ``django42``.

tox recognizes certain naming patterns and automatically sets the Python interpreter:

- ``N.M``: CPython N.M (e.g. ``3.13``) -- **preferred**
- ``pyNM`` or ``pyN.M``: CPython N.M (e.g. ``py313`` or ``py3.13``) -- legacy, still supported
- ``pypyNM``: PyPy N.M
- ``cpythonNM``: CPython N.M
- ``graalpyNM``: GraalPy N.M

Prefer the ``N.M`` form (e.g. ``3.14``) over ``pyNMM`` (e.g. ``py314``). The dotted form is unambiguous, reads more
naturally in environment lists and CI output, and avoids confusion for Python versions >= 3.10 where the concatenated
digits become three characters.

If the name doesn't match any pattern, tox uses the same Python as the one tox is installed into (this is the case for
``lint`` in our example).

For the full list of environment options, see :ref:`conf-testenv`.

***************************
 Running your environments
***************************

Run all default environments (those listed in :ref:`env_list`):

.. code-block:: bash

    tox

Run a specific environment:

.. code-block:: bash

    tox run -e lint

Run multiple environments:

.. code-block:: bash

    tox run -e 3.13,lint

Pass extra arguments to the underlying tool using ``--``:

.. code-block:: bash

    # Run pytest in verbose mode
    tox run -e 3.13 -- -v

    # Run ruff on a specific file
    tox run -e lint -- src/mymodule.py

The ``{ replace = "posargs" }`` in TOML (or ``{posargs}`` in INI) is a placeholder that gets replaced by whatever you
pass after ``--``.

**************************
 Understanding the output
**************************

On the first run, tox creates virtual environments and installs dependencies. Subsequent runs reuse existing
environments unless dependencies change:

.. code-block:: bash

    $ tox run -e 3.13,lint
    3.13: install_deps> python -m pip install 'pytest>=8'
    3.13: commands[0]> pytest tests
    ========================= 3 passed in 0.12s =========================
    3.13: OK ✔ in 5.43s
    lint: install_deps> python -m pip install ruff
    lint: commands[0]> ruff check .
    All checks passed!
    lint: OK ✔ in 2.11s

      3.13: OK (5.43=setup[3.21]+cmd[2.22] seconds)
      lint: OK (2.11=setup[1.05]+cmd[1.06] seconds)
      congratulations :)

tox will automatically detect changes to your dependencies and recreate environments when needed. You can force a full
recreation with the ``-r`` flag:

.. code-block:: bash

    tox run -e 3.13 -r

********************************
 Listing available environments
********************************

See all configured environments and their descriptions:

.. code-block:: bash

    $ tox list
    default environments:
    3.13 -> run the test suite with pytest
    3.12 -> run the test suite with pytest
    lint -> run linters

**************************
 Inspecting configuration
**************************

View the resolved configuration for an environment:

.. code-block:: bash

    tox config -e 3.13 -k deps commands

This is useful for debugging configuration issues.

************
 Next steps
************

Now that you have a working tox setup, explore these topics:

- :doc:`user_guide` -- understand how tox works (parallel mode, packaging, auto-provisioning)
- :doc:`howto` -- practical recipes for common tasks
- :ref:`configuration` -- full configuration reference
- :ref:`cli` -- complete CLI reference
