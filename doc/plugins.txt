.. be in -*- rst -*- mode!

tox plugins
===========

.. versionadded:: 2.0

With tox-2.0 a few aspects of tox running can be experimentally modified
by writing hook functions.  The list of of available hook function is
to grow over time on a per-need basis.


writing a setuptools entrypoints plugin
---------------------------------------

If you have a ``tox_MYPLUGIN.py`` module you could use the following
rough ``setup.py`` to make it into a package which you can upload to the
Python packaging index::

    # content of setup.py
    from setuptools import setup

    if __name__ == "__main__":
        setup(
            name='tox-MYPLUGIN',
            description='tox plugin decsription',
            license="MIT license",
            version='0.1',
            py_modules=['tox_MYPLUGIN'],
            entry_points={'tox': ['MYPLUGIN = tox_MYPLUGIN']},
            install_requires=['tox>=2.0'],
        )

If installed, the ``entry_points`` part will make tox see and integrate
your plugin during startup.

You can install the plugin for development ("in-place") via::

    pip install -e .

and later publish it via something like::

    python setup.py sdist register upload


Writing hook implementations
----------------------------

A plugin module defines one or more hook implementation functions
by decorating them with tox's ``hookimpl`` marker::

    from tox import hookimpl

    @hookimpl
    def tox_addoption(parser):
        # add your own command line options


    @hookimpl
    def tox_configure(config):
        # post process tox configuration after cmdline/ini file have
        # been parsed

If you put this into a module and make it pypi-installable with the ``tox``
entry point you'll get your code executed as part of a tox run.



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
