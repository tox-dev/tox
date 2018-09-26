tox installation
==================================

Install info in a nutshell
----------------------------------

**Pythons**: CPython 2.7 and 3.4 or later, Jython-2.5.1, pypy-1.9ff

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

.. include:: links.rst
