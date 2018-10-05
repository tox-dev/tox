.. _developers:

Developers FAQ
==============
This section contains information for users who want to extend the tox source code.

.. contents::
   :local:

PyCharm
-------
1. To generate the **project interpreter** you can use ``tox -rvvve dev``.
2. For tests we use **pytest**, therefore change the `Default test runner <https://www.jetbrains.com/help/pycharm/python-integrated-tools.html>`_ to ``pytest``.
3. In order to be able to **debug** tests which create
   a virtual environment (the ones in ``test_z_cmdline.py``) one needs to disable the PyCharm feature
   `Attach to subprocess automatically while debugging <https://www.jetbrains.com/help/pycharm/python-debugger.html>`_
   (because virtualenv creation calls via subprocess to the ``pip`` executable, and PyCharm rewrites all calls to
   Python interpreters to attach to its debugger - however, this rewrite for pip makes it to have bad arguments:
   ``no such option --port``).

Multiple Python versions on Windows
-----------------------------------
In order to run the unit tests locally all Python versions enlisted in ``tox.ini`` need to be installed.

.. note:: For a nice Windows terminal take a look at `cmder`_.

.. _cmder: http://cmder.net/

One solution for this is to install the latest conda, and then install all Python versions via conda envs. This will
create separate folders for each Python version.

.. code-block:: bat

    conda create -n python2.7 python=2.7 anaconda

For tox to find them you'll need to:

- add the main installation version to the systems ``PATH`` variable (e.g. ``D:\Anaconda`` - you can use `WindowsPathEditor`_)
- for other versions create a BAT scripts into the main installation folder to delegate the call to the correct Python
  interpreter:

  .. code-block:: bat

     @echo off
     REM python2.7.bat
     @D:\Anaconda\pkgs\python-2.7.13-1\python.exe %*

.. _WindowsPathEditor: https://rix0rrr.github.io/WindowsPathEditor/

This way you can also directly call from cli the matching Python version  if you need to(similarly to UNIX systems), for
example:

  .. code-block:: bat

     python2.7 main.py
     python3.6 main.py
