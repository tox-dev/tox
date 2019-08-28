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
    deps = nose
    # ``{posargs}`` will be substituted with positional arguments from command line
    commands = nosetests {posargs}

you can invoke ``tox`` in the directory where your ``tox.ini`` resides.
``tox`` will sdist-package your project create two virtualenv environments
with the ``python2.7`` and ``python3.6`` interpreters, respectively, and will
then run the specified test command.


More examples?
------------------------------------------

Also you might want to checkout :doc:`general` and :doc:`documentation`.

.. include:: ../links.rst
