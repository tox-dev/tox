Packaging
=========

Although one can use tox to develop and test applications one of its most popular
usage is to help library creators. Libraries need first to be packaged, so then
they can be installed inside a virtual environment for testing. To help with this
tox implements PEP-517_ and PEP-518_. This means that by default
tox will build source distribution out of source trees. Before running test commands
``pip`` is used to install the source distribution inside the build environment.

To create a source distribution there are multiple tools out there and with PEP-517_ and PEP-518_
you can easily use your favorite one with tox. Historically tox
only supported ``setuptools``, and always used the tox host environment to build
a source distribution from the source tree. This is still the default behavior.
To opt out of this behaviour you need to set isolated builds to true.

setuptools
----------
Using the ``pyproject.toml`` file at the root folder (alongside ``setup.py``) one can specify
build requirements.

.. code-block:: toml

    [build-system]
    requires = [
        "setuptools >= 35.0.2",
        "setuptools_scm >= 2.0.0, <3"
    ]
    build-backend = "setuptools.build_meta"

.. code-block:: ini

   # tox.ini
   [tox]
   isolated_build = True

flit
----
flit_ requires ``Python 3``, however the generated source
distribution can be installed under ``python 2``. Furthermore it does not require a ``setup.py``
file as that information is also added to the ``pyproject.toml`` file.

.. code-block:: toml

    [build-system]
    requires = ["flit_core >=2,<4"]
    build-backend = "flit_core.buildapi"

    [tool.flit.metadata]
    module = "package_toml_flit"
    author = "Happy Harry"
    author-email = "happy@harry.com"
    home-page = "https://github.com/happy-harry/is"

.. code-block:: ini

   # tox.ini
   [tox]
   isolated_build = True

poetry
------
poetry_ requires ``Python 3``, however the generated source
distribution can be installed under ``python 2``. Furthermore it does not require a ``setup.py``
file as that information is also added to the ``pyproject.toml`` file.

.. code-block:: toml

    [build-system]
    requires = ["poetry_core>=1.0.0"]
    build-backend = "poetry.core.masonry.api"

    [tool.poetry]
    name = "package_toml_poetry"
    version = "0.1.0"
    description = ""
    authors = ["Name <email@email.com>"]

.. code-block:: ini

   # tox.ini
   [tox]
   isolated_build = True

   [tox:.package]
   # note tox will use the same python version as under what tox is installed to package
   # so unless this is python 3 you can require a given python version for the packaging
   # environment via the basepython key
   basepython = python3

.. include:: ../links.rst
