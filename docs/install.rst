tox installation
==================================

Install info in a nutshell
----------------------------------

**Pythons**: CPython 2.7 and 3.5 or later, Jython-2.5.1, pypy-1.9ff

**Operating systems**: Linux, Windows, OSX, Unix

**Installer Requirements**: setuptools_

**License**: MIT license

**git repository**: https://github.com/tox-dev/tox

Installation with pip
--------------------------------------

Use the following command:

.. code-block:: shell

   pip install tox

It is fine to install ``tox`` itself into a virtualenv_ environment.

Install from clone
-------------------------

Consult the GitHub page how to clone the git repository:

    https://github.com/tox-dev/tox

and then install in your environment with something like:

.. code-block:: shell

    $ cd <path/to/clone>
    $ pip install .

or install it `editable <https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs>`_ if you want code changes to propagate automatically:

.. code-block:: shell

    $ cd <path/to/clone>
    $ pip install --editable .

so that you can do changes and submit patches.


[Linux/macOS] Install via your package manager
----------------------------------------------

You can also find tox packaged for many Linux distributions and Homebrew for macOs - usually under the name of **python-tox** or simply **tox**. Be aware though that there also other projects under the same name (most prominently a `secure chat client <https://tox.chat/>`_ with no affiliation to this project), so make sure you install the correct package.

Installation of all additional Python versions
------------------------------------------

As you install ``tox`` for different projects, you may notice that it wants to run tests with different versions of Python,
some of which are not installed on your system.
This section aims to help you further by providing an overview over different guides that help installing and using
different versions of Python next to each other on one operating system.

What this is not:

- We do not endorse any specific way of installing Python here.
- We do not give support for how to **install** Python. ``tox`` is for **testing**. You will get help somewhere else.

Which versions to install
~~~~~~~~~~~~~~~~~~~~~~~~~

If you run ``tox``, it will run tests with the Python versions installed and fail or warn for those versions that are not installed.
The ``tox.ini`` file should also give a clue.

.. code::

      ___________________________________ summary ____________________________________
        py27: commands succeeded
      ERROR:  py36: InterpreterNotFound: python3.6
      ERROR:  py37: InterpreterNotFound: python3.7
      ERROR:  py38: InterpreterNotFound: python3.8
      ERROR:  py39: InterpreterNotFound: python3.9
        py310: commands succeeded
      ERROR:  pypy3: InterpreterNotFound: pypy3

Linux
~~~~~

Have a look at these guides on how to install multiple versions of Python on Linux. If you find a new one, please add it!

- Depending on the distribution of your choice, you might be able to install additional Python versions via your package manager.
- `pyenv <https://github.com/pyenv/pyenv#installation>`_
- `Deadsnakes PPA for Ubuntu <https://launchpad.net/~deadsnakes/+archive/ubuntu/ppa>`_
- `build Python from source <https://docs.python.org/3/using/unix.html#building-python>`_

Windows
~~~~~~~

Have a look at these guides on how to install multiple versions of Python on Windows. If you find a new one, please add it!

- `pyenv-win <https://github.com/pyenv-win/pyenv-win#installation>`_
- `choosing the right location for manual installations <https://stackoverflow.com/questions/13834381/set-up-multiple-python-installations-on-windows-with-tox>`_

MacOS
~~~~~

Have a look at these guides on how to install multiple versions of Python on MacOS. If you find a new one, please add it!

- `pyenv`_


.. include:: links.rst
