User Guide
==========

Overview
--------

tox is an environment orchestrator. Use it to define how to setup and execute various tools on your projects. The
tool can set up environments for and invoke:

- test runners (such as :pypi:`pytest`),
- linters (e.g., :pypi:`flake8`),
- formatters (for example :pypi:`black` or :pypi:`isort`),
- documentation generators (e.g., :pypi:`Sphinx`),
- build and publishing tools (e.g., :pypi:`build` with :pypi:`twine`),
- ...

Configuration
-------------

*tox* needs a configuration file where you define what tools you need to run and how to provision a test environment for
these. The canonical file for this is either a ``tox.toml`` or ``tox.ini`` file. For example:

    .. tab:: TOML

       .. code-block:: toml

            requires = ["tox>=4"]
            env_list = ["lint", "type", "3.13", "3.12", "3.11"]

            [env_run_base]
            description = "run unit tests"
            deps = [
                "pytest>=8",
                "pytest-sugar"
            ]
            commands = [["pytest", { replace = "posargs", default = ["tests"], extend = true }]]

            [env.lint]
            description = "run linters"
            skip_install = true
            deps = ["black"]
            commands = [["black", { replace = "posargs", default = ["."], extend = true} ]]

            [env.type]
            description = "run type checks"
            deps = ["mypy"]
            commands = [["mypy", { replace = "posargs", default = ["src", "tests"], extend = true} ]]


    .. tab:: INI

       .. code-block:: ini

            [tox]
            requires =
                tox>=4
            env_list = lint, type, 3.1{3,2,1}

            [testenv]
            description = run unit tests
            deps =
                pytest>=8
                pytest-sugar
            commands =
                pytest {posargs:tests}

            [testenv:lint]
            description = run linters
            skip_install = true
            deps =
                black
            commands = black {posargs:.}

            [testenv:type]
            description = run type checks
            deps =
                mypy
            commands =
                mypy {posargs:src tests}

.. tip::

   You can also generate a ``tox.ini`` file automatically by running ``tox quickstart`` and then answering a few
   questions.

The configuration is split into two types:

- core settings
- tox environment settings.

Core settings
~~~~~~~~~~~~~

Core settings that affect all test environments or configure how tox itself is invoked are defined under the root table
in ``tox.toml`` and ``tox`` section in ``tox.ini``.

    .. tab:: TOML

       .. code-block:: toml

          requires = ["tox>=4"]
          env_list = ["lint", "type", "3.13", "3.12", "3.11"]

    .. tab:: INI

       .. code-block:: ini

        [tox]
        requires =
            tox>=4
        env_list = lint, type, 3.1{3,2,1}


We can use it to specify things such as the minimum version of *tox* required or the location of the package under test.
A list of all supported configuration options for the ``tox`` section can be found in the :ref:`configuration guide
<conf-core>`.

Test environments
~~~~~~~~~~~~~~~~~

When ``<env_name>`` is the name of a specific environment, test environment configurations are defined:

- ``testenv`` section and individual ``testenv:<env_name>`` for ``tox.ini``,
- ``env_run_base`` table and individual ``env.<env_name>`` for ``tox.toml``.

.. tab:: TOML

   .. code-block:: toml

        [env_run_base]
        description = "run unit tests"
        deps = [
            "pytest>=8",
            "pytest-sugar"
        ]
        commands = [["pytest", { replace = "posargs", default = ["tests"], extend = true }]]

        [env.lint]
        description = "run linters"
        skip_install = true
        deps = ["black"]
        commands = [["black", { replace = "posargs", default = ["."], extend = true} ]]

        [env.type]
        description = "run type checks"
        deps = ["mypy"]
        commands = [["mypy", { replace = "posargs", default = ["src", "tests"], extend = true} ]]

.. tab:: INI

   .. code-block:: ini

    [testenv]
    description = run unit tests
    deps =
        pytest>=8
        pytest-sugar
    commands =
        pytest {posargs:tests}

    [testenv:lint]
    description = run linters
    skip_install = true
    deps =
        black
    commands = black {posargs:.}

    [testenv:type]
    description = run type checks
    deps =
        mypy
    commands =
        mypy {posargs:src tests}

Settings defined at the top-level (``env_run_base`` table in TOML and ``testenv`` section in INI configuration files)
are automatically inherited by individual environments unless overridden. Test environment names can consist of
alphanumeric characters and dashes; for example: ``py311-django42``. The name will be split on dashes into multiple
factors, meaning ``py311-django42`` will be split into two factors: ``py311`` and ``django42``. *tox* defines a number
of default factors, which correspond to various versions and implementations of Python and provide default values for
``base_python``:

- ``pyNM``: configures ``basepython = pythonN.M``
- ``pypyNM``: configures ``basepython = pypyN.M``
- ``jythonNM``: configures ``basepython = jythonN.M``
- ``cpythonNM``: configures ``basepython = cpythonN.M``
- ``ironpythonNM``: configures ``basepython = ironpythonN.M``
- ``rustpythonNM``: configures ``basepython = rustpythonN.M``
- ``graalpyNM``: configures ``basepython = graalpyN.M``

You can also specify these factors with a period between the major and minor versions (e.g. ``pyN.M``), without a minor
version (e.g. ``pyN``), or without any version information whatsoever (e.g. ``py``)

A list of all supported configuration options for the tox environments can be found in the
:ref:`configuration guide <conf-testenv>`.

Basic example
-------------

.. tab:: TOML

   .. code-block:: toml


        env_list =  ["format", "3.13"]

        [env.format]
        description = "install black in a virtual environment and invoke it on the current folder"
        deps = ["black==22.3.0"]
        skip_install = true
        commands = [[ "black", "." ]]

        [env."3.13"]
        description = "install pytest in a virtual environment and invoke it on the tests folder"
        deps = [
            "pytest>=7",
            "pytest-sugar",
        ]
        commands = [[ "pytest", "tests", { replace = "posargs", extend = true} ]]

.. tab:: INI

   .. code-block:: ini

        [tox]
        env_list =
            format
            3.13

        [testenv:format]
        description = install black in a virtual environment and invoke it on the current folder
        deps = black==22.3.0
        skip_install = true
        commands = black .

        [testenv:3.13]
        description = install pytest in a virtual environment and invoke it on the tests folder
        deps =
            pytest>=7
            pytest-sugar
        commands = pytest tests {posargs}

This example contains a core configuration (root table in TOML and ``tox`` in INI) section as well as two
test environments. Taking the core section first, we use the :ref:`env_list` setting to indicate that this project has
two run environments named ``format`` and ``3.13`` that should be run by default when ``tox run`` is invoked without a
specific environment.

The formatting environment and test environment are defined separately (via the ``env.format`` and ``env."3.13"`` in
TOML file; ``testenv:format`` and ``testenv:py313`` in INI file). For example to format the project we:

- add a description (visible when you type ``tox list`` into the command line) via the :ref:`description` setting
- define that it requires the :pypi:`black` dependency with version ``22.3.0`` via the :ref:`deps` setting
- disable installation of the project under test into the test environment via the :ref:`skip_install` setting -
  ``black`` does not need it installed
- indicate the commands to be run via the :ref:`commands` setting

For testing the project we use the ``3.13`` environment. For this environment we:

- define a text description of the environment via the :ref:`description` setting
- specify that we should install :pypi:`pytest` v7.0 or later together with the :pypi:`pytest-sugar` project via the
  :ref:`deps` setting
- indicate the command(s) to be run - in this case ``pytest tests`` - via the :ref:`commands` setting

``{ replace = "posargs"}`` in TOML and ``{posargs}`` in INI is a place holder part for the CLI command that allows us to
pass additional flags to the pytest invocation, for example if we'd want to run ``pytest tests -v`` as a one off,
instead of ``tox run -e 3.13`` we'd type ``tox run -e py310 -- -v``. The ``--`` delimits flags for the tox tool and
what should be forwarded to the tool within.

tox, by default, always creates a fresh virtual environment for every run environment. The Python version to use for a
given environment can be controlled via the :ref:`base_python` configuration, however if not set tox will try to use the
environment name to determine something sensible: if the name is in the format of ``pyxy`` (or ``x.y``) then tox will
create an environment with CPython with version ``x.y`` (for example ``py310`` means CPython ``3.10``). If the name does
not match this pattern it will use a virtual environment with the same Python version as the one tox is installed into
(this is the case for ``format``).

tox environments are reused between runs, so while the first ``tox run -e 3.13`` will take a while as tox needs to
create a virtual environment and install ``pytest`` and ``pytest-sugar`` in it, subsequent runs only need to reinstall
your project, as long as the environments dependency list does not change.

Almost every step and aspect of virtual environments and command execution can be customized. You'll find
an exhaustive list of configuration flags (together with what it does and detailed explanation of what values are
accepted) at our :ref:`configuration page <configuration>`.

System overview
---------------

Below is a graphical representation of the tox states and transition pathways between them:

.. image:: img/overview_light.svg
   :align: center
   :class: only-light

.. image:: img/overview_dark.svg
   :align: center
   :class: only-dark


The primary tox states are:

#. **Configuration:** load tox configuration files (such as ``tox.ini``, ``pyproject.toml`` and ``toxfile.py``) and
   merge it with options from the command line plus the operating system environment variables.

#. **Environment**: for each selected tox environment (e.g. ``py310``, ``format``) do:

   #. **Creation**: create a fresh environment; by default :pypi:`virtualenv` is used, but configurable via
      :ref:`runner`. For `virtualenv` tox will use the `virtualenv discovery logic
      <https://virtualenv.pypa.io/en/latest/user_guide.html#python-discovery>`_ where the python specification is
      defined by the tox environments :ref:`base_python` (if not set will default to the environments name). This is
      created at first run only to be reused at subsequent runs. If certain aspects of the project change (python
      version, dependencies removed, etc.), a re-creation of the environment is automatically triggered. To force the
      recreation tox can be invoked with the :ref:`recreate` flag (``-r``).

   #. **Install dependencies** (optional): install the environment dependencies specified inside the ``deps``
      configuration section, and then the earlier packaged source distribution. By default ``pip`` is used to install
      packages, however one can customize this via ``install_command``. Note ``pip`` will not update project
      dependencies (specified either in the ``install_requires`` or the ``extras`` section of the ``setup.py``) if any
      version already exists in the virtual environment; therefore we recommend to recreate your environments whenever
      your project dependencies change.

   #. **Packaging** (optional): create a distribution of the current project.

      #. **Build**: If the tox environment has a package configured tox will build a package from the current source
         tree. If multiple tox environments are run and the package built are compatible in between them then it will be
         reused. This is to ensure that we build the package as rare as needed. By default for Python a source
         distribution is built as defined via the ``pyproject.toml`` style build (see PEP-517 and PEP-518).

      #. **Install the package dependencies**. If this has not changed since the last run this step will be skipped.

      #. **Install the package**. This operation will force reinstall the package without its dependencies.

   #. **Commands**: run the specified commands in the specified order. Whenever the exit code of any of them is not
      zero, stop and mark the environment failed. When you start a command with a dash character, the exit code will be
      ignored.

#. **Report** print out a report of outcomes for each tox environment:

   .. code:: bash

      ____________________ summary ____________________
      py37: commands succeeded
      ERROR:   py38: commands failed

   Only if all environments ran successfully tox will return exit code ``0`` (success). In this case you'll also see the
   message ``congratulations :)``.

tox will take care of environment variable isolation for you. That means it will remove system environment variables not specified via
``passenv``. Furthermore, it will also alter the ``PATH`` variable so that your commands resolve within the current
active tox environment. In general, all executables outside of the tox environment are available in ``commands``, but
external commands need to be explicitly allowed via the :ref:`allowlist_externals` configuration.

Main features
-------------

* **automation of tedious Python related test activities**
* **test your Python package against many interpreter and dependency configurations**

  - automatic customizable (re)creation of :pypi:`virtualenv` test environments
  - installs your project into each virtual environment
  - test-tool agnostic: runs pytest, nose or unittest in a uniform manner

* ``plugin system`` to modify tox execution with simple hooks.
* uses :pypi:`pip` and :pypi:`virtualenv` by default. Support for plugins replacing it with their own.
* **cross-Python compatible**: tox requires CPython 3.9 and higher, but it can create environments 2.7 or later.
  Special configuration might be required: :ref:`eol-version-support`.
* **cross-platform**: Windows, macOS and Unix style environments
* **full interoperability with devpi**: is integrated with and is used for testing in the :pypi:`devpi` system, a
  versatile PyPI index server and release managing tool
* **driven by a simple (but flexible to allow expressing more complicated variants) ini-style config file**
* **documented** examples and configuration
* **concise reporting** about tool invocations and configuration errors
* supports using different / multiple PyPI index servers

Related projects
----------------

tox has influenced several other projects in the Python test automation space. If tox doesn't quite fit your needs or
you want to do more research, we recommend taking a look at these projects:

- `nox <https://nox.thea.codes/en/stable/>`__ is a project similar in spirit to tox but different in approach. The
  primary key difference is that it uses Python scripts instead of a configuration file. It might be useful if you
  find tox configuration too limiting but aren't looking to move to something as general-purpose as ``Invoke`` or
  ``make``. Please note that tox will support defining configuration in a Python file soon, too.
- `Invoke <https://www.pyinvoke.org/>`__ is a general-purpose task execution library, similar to Make. Invoke is far
  more general-purpose than tox but it does not contain the Python testing-specific features that tox specializes in.


Auto-provisioning
-----------------
In case the installed tox version does not satisfy either the :ref:`min_version` or the :ref:`requires`, tox will automatically
create a virtual environment under :ref:`provision_tox_env` name that satisfies those constraints and delegate all
calls to this meta environment. This should allow satisfying constraints on your tox environment automatically,
given you have at least version ``3.8.0`` of tox.

For example given:

.. tab:: TOML

   .. code-block:: toml

        min_version = "4"
        requires = ["tox-uv>=1"]

.. tab:: INI

   .. code-block:: ini

        [tox]
        min_version = 4
        requires = tox-uv>=1


if the user runs it with tox ``3.8`` or later the installed tox application will automatically ensure that both the minimum version and
requires constraints are satisfied, by creating a virtual environment under ``.tox`` folder, and then installing into it
``tox>=4`` and ``tox-uv>=1``. Afterwards all tox invocations are forwarded to the tox installed inside ``.tox\.tox``
folder (referred to as meta-tox or auto-provisioned tox).

This allows tox to automatically setup itself with all its plugins for the current project.  If the host tox satisfies
the constraints expressed with the :ref:`requires` and :ref:`min_version` no such provisioning is done (to avoid
setup cost and indirection when it's not explicitly needed).

Cheat sheet
------------

This section details information that you'll use most often in short form.

CLI
~~~
- Each tox subcommand has a 1 (or 2) letter shortcut form too, e.g. ``tox run`` can also be written as ``tox r`` or
  ``tox config`` can be shortened to ``tox c``.
- To run all tox environments defined in the :ref:`env_list` run tox without any flags: ``tox``.
- To run a single tox environment use the ``-e`` flag for the ``run`` sub-command as in ``tox run -e py310``.
- To run two or more tox environment pass comma separated values, e.g. ``tox run -e format,py310``. The run command will
  run the tox environments sequentially, one at a time, in the specified order.
- To run two or more tox environment in parallel use the ``parallel`` sub-command , e.g. ``tox parallel -e py39,py310``.
  The ``--parallel`` flag for this sub-command controls the degree of parallelism.
- To view the configuration value for a given environment and a given configuration key use the config sub-command with
  the ``-k`` flag to filter for targeted configuration values: ``tox config -e py310 -k pass_env``.
- tox tries to automatically detect changes to your project dependencies and force a recreation when needed.
  Unfortunately the detection is not always accurate, and it also won't detect changes on the PyPI index server. You can
  force a fresh start for the tox environments by passing the ``-r`` flag to your run command. Whenever you see
  something that should work but fails with some esoteric error it's recommended to use this flag to make sure you don't
  have a stale Python environment; e.g. ``tox run -e py310 -r`` would clean the run environment and recreate it from
  scratch.

Config files
~~~~~~~~~~~~

- Every tox environment has its own configuration section (e.g. in case of ``tox.toml`` configuration method the
  ``3.13`` tox environments configuration is read from the ``env_run_base."3.13"`` table). If the table is missing or
  does not contain that configuration value, it will fall back to the section defined by the :ref:`base` configuration
  (for ``tox.toml`` this is the ``env_run_base`` table). For example:

  .. code-block:: toml

    [env_run_base]
    commands = [["pytest", "tests"]]

    [env.test]
    description = "run the test suite with pytest"

  Here the environment description for ``test`` is taken from ``env_run_base``. As ``commands`` is not specified,
  the value defined under the ``env_run_base`` section will be used. If the base environment is also missing a
  configuration value then the configuration default will be used (e.g. in case of the ``pass_env`` configuration here).

- To change the current working directory for the commands run use :ref:`change_dir` (note this will make the change for
  all install commands too - watch out if you have relative paths in your project dependencies).

- Environment variables:
  - To view environment variables set and passed down use ``tox c -e py310 -k set_env pass_env``.
  - To pass through additional environment variables use :ref:`pass_env`.
  - To set environment variables use :ref:`set_env`.

- Setup operation can be configured via the :ref:`commands_pre`, while teardown commands via the :ref:`commands_post`.

.. _`parallel_mode`:

Parallel mode
-------------

``tox`` allows running environments in parallel mode via the ``parallel`` sub-command:

- After the packaging phase completes tox will run the tox environments in parallel processes (multi-thread based).
- the ``--parallel``  flag takes an argument specifying the degree of parallelization, defaulting to ``auto``:

  - ``all`` to run all invoked environments in parallel,
  - ``auto`` to limit it to CPU count,
  - or pass an integer to set that limit.
- Parallel mode displays a progress spinner while running tox environments in parallel, and reports outcome of these as
  soon as they have been completed with a human readable duration timing attached. To run parallelly without the spinner,
  you can use the ``--parallel-no-spinner`` flag.
- Parallel mode by default shows output only of failed environments and ones marked as :ref:`parallel_show_output`
  ``=True``.
- There's now a concept of dependency between environments (specified via :ref:`depends`), tox will re-order the
  environment list to be run to satisfy these dependencies, also for sequential runs. Furthermore, in parallel mode,
  tox will only schedule a tox environment to run once all of its dependencies have finished (independent of their outcome).

  .. warning::

    ``depends`` does not pull in dependencies into the run target, for example if you select ``py310,py39,coverage``
    via the ``-e`` tox will only run those three (even if ``coverage`` may specify as ``depends`` other targets too -
    such as ``py310, py39, py38, py37``).

- ``--parallel-live``/``-o`` allows showing the live output of the standard output and error, also turns off reporting
  as described above.
- Note: parallel evaluation disables standard input. Use non parallel invocation if you need standard input.

Example final output:

.. code-block:: bash

    $ tox -e py310,py39,coverage -p all
    ✔ OK py39 in 9.533 seconds
    ✔ OK py310 in 9.96 seconds
    ✔ OK coverage in 2.0 seconds
    ___________________________ summary ______________________________________________________
      py310: commands succeeded
      py39: commands succeeded
      coverage: commands succeeded
      congratulations :)


Example progress bar, showing a rotating spinner, the number of environments running and their list (limited up to
120 characters):

.. code-block:: bash

    ⠹ [2] py310 | py39

Packaging
---------

tox always builds projects in a PEP-518 compatible virtual environment and communicates with the build backend according
to the interface defined in PEP-517 and PEP-660. To define package build dependencies and specify the build backend to
use create a ``pyproject.toml`` at the root of the project. For example to use hatch:

.. code-block:: toml

    [build-system]
    build-backend = "hatchling.build"
    requires = ["hatchling>=0.22", "hatch-vcs>=0.2"]

By default tox will create and install a source distribution. You can configure to build a wheel instead by setting
the :ref:`package` configuration to ``wheel``. Wheels are much faster to install than source distributions.

To query the projects dependencies tox will use a virtual environment whose name is defined under the :ref:`package_env`
configuration (by default ``.pkg``). The virtual environment used for building the package depends on the artifact
built:

- for source distribution the :ref:`package_env`,
- for wheels the name defined under :ref:`wheel_build_env` (this depends on the Python version defined by the target tox
  environment under :ref:`base_python`,  if the environment targets CPython 3.10 it will be ``.pkg-cpython310`` or
  for PyPy 3.9 it will be ``.pkg-pypy39``).

For pure Python projects (non C-Extension ones) it's recommended to set :ref:`wheel_build_env` to the same as the
:ref:`package_env`. This way you'll build the wheel once and install the same wheel for all tox environments.

Advanced features
-----------------

Disallow command line environments which are not explicitly specified in the config file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Previously, any environment would be implicitly created even if no such environment was specified in the configuration
file. For example, given this config:

.. tab:: TOML

   .. code-block:: toml

        [env.unit]
        deps = [ "pytest" ]
        commands = [[ "pytest" ]]

.. tab:: INI

   .. code-block:: ini

        [testenv:unit]
        deps = pytest
        commands = pytest

Running ``tox -e unit`` would run our tests but running ``tox -e unt`` or ``tox -e unti`` would ultimately succeed
without running any tests. A special exception is made for environments starting in ``py*``. In the above example
running ``tox -e py310`` would still function as intended.
