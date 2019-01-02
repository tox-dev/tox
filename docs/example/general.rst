.. be in -*- rst -*- mode!

General tips and tricks
================================

Interactively passing positional arguments
-----------------------------------------------

If you invoke ``tox`` like this:

.. code-block:: shell

    tox -- -x tests/test_something.py

the arguments after the ``--`` will be substituted
everywhere where you specify ``{posargs}`` in your
test commands, for example using ``pytest``:

.. code-block:: ini

    [testenv]
    # Could also be in a specific ``[testenv:<NAME>]`` section
    commands = pytest {posargs}

or using ``nosetests``:

.. code-block:: ini

    [testenv]
    commands = nosetests {posargs}

the above ``tox`` invocation will trigger the test runners to
stop after the first failure and to only run a particular test file.

You can specify defaults for the positional arguments using this
syntax:

.. code-block:: ini

    [testenv]
    commands = nosetests {posargs:--with-coverage}

.. _recreate:

Dependency changes and tracking
-------------------------------

Creating virtual environments and installing dependencies is a expensive operation.
Therefore tox tries to avoid it whenever possible, meaning it will never perform this
unless it detects with absolute certainty that it needs to perform an update. A tox
environment creation is made up of:

- create the virtual environment
- install dependencies specified inside deps
- if it's a library project (has build package phase), install library dependencies
  (with potential extras)

These three steps are only performed once (given they all succeeded). Subsequent calls
that don't detect changes to the traits of that step will not alter the virtual
environment in any way. When a change is detected for any of the steps, the entire
virtual environment is removed and the operation starts from scratch (this is
because it's very hard to determine what would the delta changes would be needed -
e.g. a dependency could migrate from one dependency to another, and in this case
we would need to install the new while removing the old one).

Here's what traits we track at the moment for each steps:

- virtual environment trait is tied to the python path the :conf:`basepython`
  resolves too (if this config changes, the virtual environment will be recreated),
- :conf:`deps` sections changes (meaning any string-level change for the entries, note
  requirement file content changes are not tracked),
- library dependencies are tracked at :conf:`extras` level (because there's no
  Python API to enquire about the actual dependencies in a non-tool specific way,
  e.g. setuptools has one way, flit something else, and poetry another).

Whenever you change traits that are not tracked we recommend you to manually trigger a
rebuild of the tox environment by passing the ``-r`` flag for the tox invocation. For
instance, for a setuptools project whenever you modify the ``install_requires`` keyword
at the next run force the recreation of the tox environment by passing the recreate cli
tox flag.

.. _`TOXENV`:

Selecting one or more environments to run tests against
--------------------------------------------------------

Using the ``-e ENV[,ENV36,...]``  option you explicitly list
the environments where you want to run tests against. For
example, given the previous sphinx example you may call:

.. code-block:: shell

    tox -e docs

which will make ``tox`` only manage the ``docs`` environment
and call its test commands.  You may specify more than
one environment like this:

.. code-block:: shell

    tox -e py27,py36

which would run the commands of the ``py27`` and ``py36`` testenvironments
respectively.  The special value ``ALL`` selects all environments.

You can also specify an environment list in your ``tox.ini``:

.. code-block:: ini

    [tox]
    envlist = py27,py36

or override it from the command line or from the environment variable
``TOXENV``:

.. code-block:: shell

    export TOXENV=py27,py36 # in bash style shells

.. _artifacts:

Access package artifacts between multiple tox-runs
--------------------------------------------------------

If you have multiple projects using tox you can make use of
a ``distshare`` directory where ``tox`` will copy in sdist-packages so
that another tox run can find the "latest" dependency.  This feature
allows to test a package against an unreleased development version
or even an uncommitted version on your own machine.

By default, ``{homedir}/.tox/distshare`` will be used for
copying in and copying out artifacts (i.e. Python packages).

For project ``two`` to depend on the ``one`` package you use
the following entry:

.. code-block:: ini

    # example two/tox.ini
    [testenv]
    # install latest package from "one" project
    deps = {distshare}/one-*.zip

That's all.  tox running on project ``one`` will copy the sdist-package
into the ``distshare`` directory after which a ``tox`` run on project
``two`` will grab it because ``deps`` contain an entry with the
``one-*.zip`` pattern.  If there is more than one matching package the
highest version will be taken.  ``tox`` uses verlib_  to compare version
strings which must be compliant with :pep:`386`.

If you want to use this with Jenkins_, also checkout the :ref:`jenkins artifact example`.

.. _verlib: https://bitbucket.org/tarek/distutilsversion/

basepython defaults, overriding
+++++++++++++++++++++++++++++++

For any ``pyXY`` test environment name the underlying ``pythonX.Y`` executable
will be searched in your system ``PATH``. Similarly, for ``jython`` and
``pypy`` the respective ``jython`` and ``pypy-c`` names will be looked for.
The executable must exist in order to successfully create *virtualenv*
environments. On Windows a ``pythonX.Y`` named executable will be searched in
typical default locations using the ``C:\PythonX.Y\python.exe`` pattern.

All other targets will use the system ``python`` instead. You can override any
of the default settings by defining the :conf:`basepython` variable in a
specific test environment section, for example:

.. code-block:: ini

    [testenv:docs]
    basepython = python2.7

Avoiding expensive sdist
------------------------

Some projects are large enough that running an sdist, followed by
an install every time can be prohibitively costly. To solve this,
there are two different options you can add to the ``tox`` section. First,
you can simply ask tox to please not make an sdist:

.. code-block:: ini

    [tox]
    skipsdist=True

If you do this, your local software package will not be installed into
the virtualenv. You should probably be okay with that, or take steps
to deal with it in your commands section:

.. code-block:: ini

    [testenv]
    commands = python setup.py develop
               pytest

Running ``setup.py develop`` is a common enough model that it has its own
option:

.. code-block:: ini

    [testenv]
    usedevelop=True

And a corresponding command line option ``--develop``, which will set
``skipsdist`` to True and then perform the ``setup.py develop`` step at the
place where ``tox`` normally performs the installation of the sdist.
Specifically, it actually runs ``pip install -e .`` behind the scenes, which
itself calls ``setup.py develop``.

There is an optimization coded in to not bother re-running the command if
``$projectname.egg-info`` is newer than ``setup.py`` or ``setup.cfg``.

.. include:: ../links.rst


Understanding ``InvocationError`` exit codes
--------------------------------------------

When a command (defined by ``commands =`` in ``tox.ini``) fails,
it has a non-zero exit code,
and an ``InvocationError`` exception is raised by ``tox``:

.. code-block:: shell

    ERROR: InvocationError for command
           '<command defined in tox.ini>' (exited with code 1)

If the command starts with ``pytest`` or ``python setup.py test`` for instance,
then the `pytest exit codes`_ are relevant.

On unix systems, there are some rather `common exit codes`_.
This is why for exit codes larger than 128,
if a signal with number equal to ``<exit code> - 128`` is found
in the :py:mod:`signal` module, an additional hint is given:

.. code-block:: shell

    ERROR: InvocationError for command
           '<command>' (exited with code 139)
    Note: this might indicate a fatal error signal (139 - 128 = 11: SIGSEGV)

where ``<command>`` is the command defined in ``tox.ini``, with quotes removed.

The signal numbers (e.g. 11 for a segmentation fault) can be found in the
"Standard signals" section of the `signal man page`_.
Their meaning is described in `POSIX signals`_.

Beware that programs may issue custom exit codes with any value,
so their documentation should be consulted.


Sometimes, no exit code is given at all.
An example may be found in `pytest-qt issue #170`_,
where Qt was calling ``abort()`` instead of ``exit()``.

.. seealso:: :ref:`ignoring exit code`.

.. _`pytest exit codes`: https://docs.pytest.org/en/latest/usage.html#possible-exit-codes
.. _`common exit codes`: http://www.faqs.org/docs/abs/HTML/exitcodes.html
.. _`abort()``: http://www.unix.org/version2/sample/abort.html
.. _`pytest-qt issue #170`: https://github.com/pytest-dev/pytest-qt/issues/170
.. _`signal man page`: http://man7.org/linux/man-pages/man7/signal.7.html
.. _`POSIX signals`: https://en.wikipedia.org/wiki/Signal_(IPC)#POSIX_signals
