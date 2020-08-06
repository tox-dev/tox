=======================
Development environment
=======================

tox can be used for just preparing different virtual environments required by a
project.

This feature can be used by deployment tools when preparing deployed project
environments. It can also be used for setting up normalized project development
environments and thus help reduce the risk of different team members using
mismatched development environments.


Creating development environments using the ``--devenv`` option
===============================================================

The easiest way to set up a development environment is to use the ``--devenv``
option along with your existing configured ``testenv``\ s.  The ``--devenv``
option accepts a single argument, the location you want to create a development
environment at.

For example, if I wanted to replicate the ``py36`` environment, I could run::

    $ tox --devenv venv-py36 -e py36
    ...
    $ source venv-py36/bin/activate
    (venv-py36) $ python --version
    Python 3.6.7

The ``--devenv`` option skips the ``commands=`` section of that configured
test environment and always sets ``usedevelop=true`` for the environment that
is created.

If you don't specify an environment with ``-e``, the devenv feature will
default to ``-e py`` -- usually taking the interpreter you're running ``tox``
with and the default ``[testenv]`` configuration.

It is possible to use the ``--devenv`` option without a tox configuration file,
however the configuration file is respected if present.

Creating development environments using configuration
=====================================================

Here are some examples illustrating how to set up a project's development
environment using tox. For illustration purposes, let us call the development
environment ``dev``.


Example 1: Basic scenario
-------------------------

Step 1 - Configure the development environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First, we prepare the tox configuration for our development environment by
defining a ``[testenv:dev]`` section in the project's ``tox.ini``
configuration file:

.. code-block:: ini

    [testenv:dev]
    basepython = python2.7
    usedevelop = True

In it we state:

- what Python executable to use in the environment,
- that our project should be installed into the environment using ``setup.py
  develop``, as opposed to building and installing its source distribution using
  ``setup.py install``.

The development environment will reside in ``toxworkdir`` (default is ``.tox``) just
like the other tox environments.

We can configure a lot more, if we want to. For example, we can add the
following to our configuration, telling tox not to reuse ``commands`` or
``deps`` settings from the base ``[testenv]``
configuration:

.. code-block:: ini

    [testenv:dev]
    commands =
    deps =


Step 2 - Create the development environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once the ``[testenv:dev]`` configuration section has been defined, we create
the actual development environment by running the following:

.. code-block:: shell

    tox -e dev

This creates the environment at the path specified by the environment's
``envdir`` configuration value.


Example 2: A more complex scenario
----------------------------------

Let us say we want our project development environment to:

- use Python executable ``python2.7``,
- pull packages from ``requirements.txt``, located in the same directory as
  ``tox.ini``.

Here is an example configuration for the described scenario:

.. code-block:: ini

    [testenv:dev]
    basepython = python2.7
    usedevelop = True
    deps = -rrequirements.txt
