.. be in -*- rst -*- mode!

tox plugins
===========

.. versionadded:: 2.0

A growing number of `pluggy`_ hooks make tox extendable by writing plugins.


Writing a setuptools entrypoints plugin
---------------------------------------

You can create a new tox plugin with all bells and whistles via `Cookiecutter`_ (see `cookiecutter-tox-plugin <https://github.com/tox-dev/cookiecutter-tox-plugin>`_):

.. code-block:: console

    $ pip install -U cookiecutter
    $ cookiecutter gh:tox-dev/cookiecutter-tox-plugin

This will create a complete pypi-releasable, documented project with license, documentation,
CI builds and other bells and whistles.

Tutorial: a minimal tox plugin
------------------------------

To create a working plugin you need at least a python project with a tox entry point and a python
module implementing one or more of the pluggy based hooks tox specifies (using the
``@tox.hookimpl`` decorator as marker).

Let us consider you want to extent tox behaviour by displaying fireworks at the end of a
successful tox run (we won't go into the details of how to display fireworks though).

minimal structure:

.. code-block:: console

    $ mkdir tox-fireworks
    $ cd tox-fireworks
    $ touch tox_fireworks.py
    $ touch setup.py

contents of ``tox_fireworks.py``:

.. code-block:: python

    import tox

    @tox.hookimpl
    def tox_addoption(parser):
        """Add command line option to display fireworks on request."""

    @tox.hookimpl
    def tox_configure(config):
        """Post process config after parsing."""

    @tox.hookimpl
    def tox_runenvreport(config):
        """Display fireworks if all was fine and requested."""


contents of ``setup.py``:

.. code-block:: python

    from setuptools import setup

    setup(name='tox-fireworks', py_modules=['tox_fireworks'],
          entry_points={'tox': ['fireworks = tox_fireworks']})

Using the  **tox-** prefix in ``tox-fireworks`` is necessary for it to be an official plugin and
makes finding it easy with e.g. ``pip search 'tox-'`` once it is released on PyPi.

To make your new plugin discoverable by tox, you need to install it. During development you should
install it with ``-e`` or ``--editable``, so that changes to the code are immediately active:

.. code-block:: console

    pip install -e </path/to/tox-fireworks>

If you think the rest of the world could profit using your plugin you can publish it to PyPi.
Add some more meta data to ``setup.py`` (see the cookiecutter for a complete example) and publish
it like:

.. code-block:: console

    $ cd </path/to/tox-fireworks>
    $ python setup.py sdist register upload


tox hook specifications and related API
---------------------------------------

.. automodule:: tox.hookspecs
    :members:

.. autoclass:: tox.config.Parser()
    :members:

.. autoclass:: tox.config.Config()
    :members:

.. autoclass:: tox.config.TestenvConfig()
    :members:

.. autoclass:: tox.venv.VirtualEnv()
    :members:

.. autoclass:: tox.session.Session()
    :members:


.. _`Cookiecutter`: https://cookiecutter.readthedocs.io
.. _`pluggy`: https://pluggy.readthedocs.io
