Installation
============

via pipx
--------

:pypi:`tox` is a CLI tool that needs a Python interpreter to run. The tool requires first to have ``Python 3.5+``
interpreter the best is to use :pypi:`pipx` to install tox into an isolated environment. This has the added
benefit that later you'll be able to upgrade tox without affecting other parts of the system.

.. code-block:: console

    pipx install tox
    tox --help

via pip
-------

Alternatively you can install it within the global Python interpreter itself (perhaps as a user package via the
``--user`` flag). Be cautious if you are using a python install that is managed by your operating system or
another package manager. ``pip`` might not coordinate with those tools, and may leave your system in an
inconsistent state. Note, if you go down this path you need to ensure pip is new enough per the subsections below:

.. code-block:: console

    python -m pip install --user tox
    python -m tox --help

wheel
~~~~~
Installing tox via a wheel (default with pip) requires an installer that can understand the ``python-requires``
tag (see `PEP-503 <https://www.python.org/dev/peps/pep-0503/>`_), with pip this is version ``9.0.0`` (released 2016
November). Furthermore, in case you're not installing it via the PyPi you need to be using a mirror that correctly
forwards the ``python-requires`` tag (notably the OpenStack mirrors don't do this, or older
`devpi <https://github.com/devpi/devpi>`_ versions - added with version ``4.7.0``).

.. _sdist:

sdist
~~~~~
When installing via a source distribution you need an installer that handles the
`PEP-517 <https://www.python.org/dev/peps/pep-0517/>`_ specification. In case of ``pip`` this is version ``18.0.0`` or
later (released on 2018 July). If you cannot upgrade your pip to support this you need to ensure that the build
requirements from `pyproject.toml <https://github.com/tox-dev/tox/blob/master/pyproject.toml#L2>`_ are satisfied
before triggering the install.

via ``setup.py``
----------------
We don't recommend and officially support this method. One should prefer using an installer that supports
`PEP-517 <https://www.python.org/dev/peps/pep-0517/>`_ interface, such as pip ``19.0.0`` or later. That being said you
might be able to still install a package via this method if you satisfy build dependencies before calling the install
command (as described under :ref:`sdist`).

latest unreleased
-----------------
Installing an unreleased version is discouraged and should be only done for testing purposes. If you do so you'll need
a pip version of at least ``18.0.0`` and use the following command:


.. code-block:: console

    pip install git+https://github.com/tox-dev/tox.git@master

.. _compatibility-requirements:

Python and OS Compatibility
---------------------------

tox works with the following Python interpreter implementations:

- `CPython <https://www.python.org/>`_ versions 3.5, 3.6, 3.7, 3.8
- `PyPy <https://pypy.org/>`_ 3.5+.

This means tox works on the latest patch version of each of these minor versions. Previous patch versions are
supported on a best effort approach. We support all platforms ``virtualenv`` supports.
