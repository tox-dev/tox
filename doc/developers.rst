.. _developers:

Developers FAQ
==============
This section contains information for users who want to extend the tox source code.

.. contents::
   :local:

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

- add the main installation version to the systems ``PATH`` variable (e.g. ``D:\Anaconda`` - you can use `patheditor2`_)
- for other versions create a BAT scripts into the main installation folder to delegate the call to the correct Python
  interpreter:
  
  .. code-block:: bat
     
     # python2.7.bat
     @D:\Anaconda\pkgs\python-2.7.13-1\python.exe %*

.. _patheditor2: https://patheditor2.codeplex.com/

This way you can also directly call from cli the matching Python version  if you need to(similarly to UNIX systems), for
example:

  .. code-block:: bat

     python2.7 main.py
     python3.6 main.py
