FAQ
===

Here you'll find answers to some frequently asked questions.

Using constraint files
----------------------
`Constraint files <https://pip.pypa.io/en/stable/user_guide/#constraints-files>`_ are a type of artifact, supported by
pip, that define not what requirements to install but instead what version constraints should be applied for the
otherwise specified requirements. The constraint file must always be specified together with the requirement(s) to
install. While creating a test environment tox will invoke pip multiple times, in separate phases:

1. If :ref:`deps` is specified, it will install a set of dependencies before installing the package.
2. If the target environment contains a package (the project does not have :ref:`package` ``skip`` or
   :ref:`skip_install` is ``true``), it will:

   1. install the dependencies of the package.
   2. install the package itself.

Some solutions and their drawbacks:

- specify the constraint files within :ref:`deps` (these constraints will not be applied when installing package
  dependencies),
- use ``PIP_CONSTRAINTS`` inside :ref:`set_env` (tox will not know about the content of the constraint file and such
  will not trigger a rebuild of the environment when its content changes),
- specify the constraint file by extending the :ref:`install_command` (tox will not know about the content of the
  constraint file and such will not trigger a rebuild of the environment when its content changes).

Note constraint files are a subset of requirement files. Therefore, it's valid to pass a constraint file wherever you
can specify a requirement file.

.. _platform-specification:

Platform specification
----------------------

Assuming the following layout:

.. code-block:: shell

    tox.ini      # see below for content
    setup.py     # a classic distutils/setuptools setup.py file

and the following ``tox.ini`` content:

.. code-block:: ini

    [tox]
    min_version = 2.0  # platform specification support is available since version 2.0
    envlist = py{310,39}-{lin,mac,win}

    [testenv]
    # environment will be skipped if regular expression does not match against the sys.platform string
    platform = lin: linux
               mac: darwin
               win: win32

    # you can specify dependencies and their versions based on platform filtered environments
    deps = lin,mac: platformdirs==3
           win: platformdirs==2

    # upon tox invocation you will be greeted according to your platform
    commands=
       lin: python -c 'print("Hello, Linus!")'
       mac: python -c 'print("Hello, Tim!")'
       win: python -c 'print("Hello, Satya!")'

You can invoke ``tox`` in the directory where your ``tox.ini`` resides. ``tox`` creates two virtualenv environments
with the ``python3.10`` and ``python3.9`` interpreters, respectively, and will then run the specified command according
to platform you invoke ``tox`` at.
