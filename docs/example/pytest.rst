pytest and tox
=================================

It is easy to integrate `pytest`_ runs with tox.  If you encounter
issues, please check if they are `listed as a known issue`_ and/or use
the :doc:`support channels <../support>`.

Basic example
--------------------------

Assuming the following layout:

.. code-block:: shell

    tox.ini      # see below for content
    setup.py     # a classic distutils/setuptools setup.py file

and the following ``tox.ini`` content:

.. code-block:: ini

    [tox]
    envlist = py35,py36

    [testenv]
    deps = pytest               # PYPI package providing pytest
    commands = pytest {posargs} # substitute with tox' positional arguments

you can now invoke ``tox`` in the directory where your ``tox.ini`` resides.
``tox`` will sdist-package your project, create two virtualenv environments
with the ``python3.5`` and ``python3.6`` interpreters, respectively, and will
then run the specified test command in each of them.

Extended example: change dir before test and use per-virtualenv tempdir
--------------------------------------------------------------------------

Assuming the following layout:

.. code-block:: shell

    tox.ini      # see below for content
    setup.py     # a classic distutils/setuptools setup.py file
    tests        # the directory containing tests

and the following ``tox.ini`` content:

.. code-block:: ini

    [tox]
    envlist = py35,py36

    [testenv]
    changedir = tests
    deps = pytest
    # change pytest tempdir and add posargs from command line
    commands = pytest --basetemp={envtmpdir} {posargs}

you can invoke ``tox`` in the directory where your ``tox.ini`` resides.
Differently than in the previous example the ``pytest`` command
will be executed with a current working directory set to ``tests``
and the test run will use the per-virtualenv temporary directory.

.. _`passing positional arguments`:

Using multiple CPUs for test runs
-----------------------------------

``pytest`` supports distributing tests to multiple processes and hosts
through the `pytest-xdist`_ plugin.  Here is an example configuration
to make ``tox`` use this feature:

.. code-block:: ini

    [testenv]
    deps = pytest-xdist
    changedir = tests
    # use three sub processes
    commands = pytest --basetemp={envtmpdir}  \
                      --confcutdir=..         \
                      -n 3                    \
                      {posargs}

.. _`listed as a known issue`:

Known Issues and limitations
-----------------------------

**Too long filenames**. you may encounter "too long filenames" for temporarily
created files in your pytest run.  Try to not use the "--basetemp" parameter.

**installed-versus-checkout version**.  ``pytest`` collects test
modules on the filesystem and then tries to import them under their
`fully qualified name`_. This means that if your test files are
importable from somewhere then your ``pytest`` invocation may end up
importing the package from the checkout directory rather than the
installed package.

This issue may be characterised by pytest test-collection error messages, in python 3.x environments, that look like:

.. code-block:: shell

    import file mismatch:
    imported module 'myproj.foo.tests.test_foo' has this __file__ attribute:
      /home/myuser/repos/myproj/build/lib/myproj/foo/tests/test_foo.py
    which is not the same as the test file we want to collect:
      /home/myuser/repos/myproj/myproj/foo/tests/test_foo.py
    HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules

There are a few ways to prevent this.

With installed tests (the tests packages are known to ``setup.py``), a
safe and explicit option is to give the explicit path
``{envsitepackagesdir}/mypkg`` to pytest.
Alternatively, it is possible to use ``changedir`` so that checked-out
files are outside the import path, then pass ``--pyargs mypkg`` to
pytest.

With tests that won't be installed, the simplest way to run them
against your installed package is to avoid ``__init__.py`` files in test
directories; pytest will still find and import them by adding their
parent directory to ``sys.path`` but they won't be copied to
other places or be found by Python's import system outside of pytest.

.. _`fully qualified name`: https://docs.pytest.org/en/latest/goodpractices.html#test-package-name

.. include:: ../links.rst
