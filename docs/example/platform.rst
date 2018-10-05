Platform specification
============================

Basic multi-platform example
----------------------------

Assuming the following layout:

.. code-block:: shell

    tox.ini      # see below for content
    setup.py     # a classic distutils/setuptools setup.py file

and the following ``tox.ini`` content:

.. code-block:: ini

    [tox]
    # platform specification support is available since version 2.0
    minversion = 2.0
    envlist = py{27,36}-{mylinux,mymacos,mywindows}

    [testenv]
    # environment will be skipped if regular expression does not match against the sys.platform string
    platform = mylinux: linux
               mymacos: darwin
               mywindows: win32

    # you can specify dependencies and their versions based on platform filtered environments
    deps = mylinux,mymacos: py==1.4.32
           mywindows: py==1.4.30

    # upon tox invocation you will be greeted according to your platform
    commands=
       mylinux: python -c 'print("Hello, Linus!")'
       mymacos: python -c 'print("Hello, Steve!")'
       mywindows: python -c 'print("Hello, Bill!")'

you can invoke ``tox`` in the directory where your ``tox.ini`` resides.
``tox`` creates two virtualenv environments with the ``python2.7`` and
``python3.6`` interpreters, respectively, and will then run the specified
command according to platform you invoke ``tox`` at.
