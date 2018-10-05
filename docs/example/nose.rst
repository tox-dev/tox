nose and tox
=================================

It is easy to integrate `nosetests`_ runs with tox.
For starters here is a simple ``tox.ini`` config to configure your project
for running with nose:

Basic nosetests example
--------------------------

Assuming the following layout:

.. code-block:: shell

    tox.ini      # see below for content
    setup.py     # a classic distutils/setuptools setup.py file

and the following ``tox.ini`` content:

.. code-block:: ini

    [testenv]
    deps=nose
    commands= nosetests [] # substitute with tox' positional arguments

you can invoke ``tox`` in the directory where your ``tox.ini`` resides.
``tox`` will sdist-package your project create two virtualenv environments
with the ``python2.7`` and ``python3.6`` interpreters, respectively, and will
then run the specified test command.


More examples?
------------------------------------------

You can use and combine other features of ``tox`` with your tox runs,
e.g. :ref:`sphinx checks`.  If you figure out some particular configurations
for nose/tox interactions please submit them.

Also you might want to checkout :doc:`general`.

.. include:: ../links.rst
