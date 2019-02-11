Contribution getting started
============================

Contributions are highly welcomed and appreciated.  Every little help counts,
so do not hesitate! If you like tox, also share some love on Twitter or in your blog posts.

.. contents:: Contribution links
   :depth: 2

.. _submitfeedback:

Feature requests and feedback
-----------------------------

We'd also like to hear about your propositions and suggestions.  Feel free to
`submit them as issues <https://github.com/tox-dev/tox/issues>`_ and:

* Explain in detail how they should work.
* Keep the scope as narrow as possible.  This will make it easier to implement.

.. _reportbugs:

Report bugs
-----------

Report bugs for tox in the `issue tracker <https://github.com/tox-dev/tox/issues>`_.

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting,
  specifically the Python interpreter version, installed libraries, and tox
  version.
* Detailed steps to reproduce the bug, or - even better, a n xfaling test reproduces the bug

If you can write a demonstration test that currently fails but should pass
(xfail), that is a very useful commit to make as well, even if you cannot
fix the bug itself (e.g. something like this in
`test_config <https://github.com/tox-dev/tox/blob/2.8.2/tests/test_config.py#L2206>)`_

.. _fixbugs:

Fix bugs
--------

Look through the GitHub issues for bugs.  Here is a filter you can use:
https://github.com/tox-dev/tox/labels/bug:normal

Don't forget to check the issue trackers of your favourite plugins, too!

.. _writeplugins:

Implement features
------------------

Look through the GitHub issues for enhancements.  Here is a filter you can use:
https://github.com/tox-dev/tox/labels/feature:new

Write documentation
-------------------

tox could always use more documentation.  What exactly is needed?

* More complementary documentation.  Have you perhaps found something unclear?
* Docstrings.  There can never be too many of them.
* Blog posts, articles and such -- they're all very appreciated.

You can also edit documentation files directly in the GitHub web interface,
without using a local copy.  This can be convenient for small fixes.

.. note::
    Build the documentation locally with the following command:

    .. code:: bash

        $ tox -e docs

    The built documentation should be available in the ``.tox/docs_out/``.

.. _submitplugin:

.. _`pull requests`:
.. _pull-requests:

Preparing Pull Requests
-----------------------

Short version
^^^^^^^^^^^^^

#. `Fork the repository <https://help.github.com/articles/fork-a-repo/>`_.
#. Make your changes.
#. open a `pull request <https://help.github.com/articles/about-pull-requests/>`_ targeting the ``master`` branch.
#. Follow **PEP-8**. There's a ``tox`` command to help fixing it: ``tox -e fix_lint``.
   You can also add a pre commit hook to your local clone to run the style checks and fixes
   (see hint after running ``tox -e fix_lint``)
#. Tests for tox are (obviously) run using ``tox``::

    tox -e fix_lint,py27,py36

   The test environments above are usually enough to cover most cases locally.

#. Consider the
   `checklist <https://github.com/tox-dev/tox/blob/master/.github/PULL_REQUEST_TEMPLATE.md>`_
   in the pull request form

Long version
^^^^^^^^^^^^

What is a "pull request"?  It informs the project's core developers about the
changes you want to review and merge.  Pull requests are stored on
`GitHub servers <https://github.com/tox-dev/tox/pulls>`_.
Once you send a pull request, we can discuss its potential modifications and
even add more commits to it later on. There's an excellent tutorial on how Pull
Requests work in the
`GitHub Help Center <https://help.github.com/articles/using-pull-requests/>`_.

Here is a simple overview, with tox-specific bits:

#. Fork the
   `tox GitHub repository <https://github.com/tox-dev/tox>`__.  It's
   fine to use ``tox`` as your fork repository name because it will live
   under your user.

#. Clone your fork locally using `git <https://git-scm.com/>`_ and create a branch::

    $ git clone git@github.com:YOUR_GITHUB_USERNAME/tox.git
    $ cd tox
    # now, to fix a bug create your own branch off "master":

        $ git checkout -b your-bugfix-branch-name master

    # or to instead add a feature create your own branch off "features":

        $ git checkout -b your-feature-branch-name features

   If you need some help with Git, follow this quick start
   guide: https://git.wiki.kernel.org/index.php/QuickStart

#. Install tox

   Of course tox is used to run all the tests of itself::

    $ cd </path/to/your/tox/clone>
    $ pip install [-e] .

#. Run all the tests

   You need to have Python 2.7 and 3.6 available in your system.  Now
   running tests is as simple as issuing this command::

    $ tox -e fix_lint,py27,py36

   This command will run tests via the "tox" tool against Python 2.7 and 3.6
   and also perform style checks with some automatic fixes.

#. You can now edit your local working copy. Please follow PEP-8.

   You can now make the changes you want and run the tests again as necessary.

    $ tox -e py27 -- --pdb

   Or to only run tests in a particular test module on Python 3.6::

    $ tox -e py36 -- testing/test_config.py

   You can also use the dev environment:

    $ tox -e dev

   To get information about all environements, type:

   $ tox -av

#. Commit and push once your tests pass and you are happy with your change(s)::

    $ git commit -a -m "<commit message>"
    $ git push -u


#. submit a pull request through the GitHub website and and consider the `checklist <https://github.com/tox-dev/tox/blob/master/.github/PULL_REQUEST_TEMPLATE.md>`_ in the pull request form::

    head-fork: YOUR_GITHUB_USERNAME/tox
    compare: your-branch-name

    base-fork: tox-dev/tox
    base: master

Submitting plugins to tox-dev
-----------------------------

tox development of the core, some plugins and support code happens
in repositories living under the ``tox-dev`` organisation:

- `tox-dev on GitHub <https://github.com/tox-dev>`_

All tox-dev team members have write access to all contained
repositories.  tox core and plugins are generally developed
using `pull requests`_ to respective repositories.

The objectives of the ``tox-dev`` organisation are:

* Having a central location for popular tox plugins
* Sharing some of the maintenance responsibility (in case a maintainer no
  longer wishes to maintain a plugin)

You can submit your plugin by opening an `issue <https://github.com/tox-dev/tox/issues/new>`_
requesting to add you as a member of tox-dev to be able to integrate the plugin.
As a member of the or you can then transfer the plugin yourself.

The plugin must have the following:

- PyPI presence with a ``setup.py`` that contains a license, ``tox-``
  prefixed name, version number, authors, short and long description.

- a ``tox.ini`` for running tests using `tox <https://tox.readthedocs.io>`_.

- a ``README`` describing how to use the plugin and on which
  platforms it runs.

- a ``LICENSE`` file or equivalent containing the licensing
  information, with matching info in ``setup.py``.

- an issue tracker for bug reports and enhancement requests.

- a `changelog <https://keepachangelog.com/>`_

If no contributor strongly objects, the repository can then be
transferred to the ``tox-dev`` organisation. For details see
`about repository transfers <https://help.github.com/articles/about-repository-transfers/>`_

Members of the tox organization have write access to all projects.
We recommend that each plugin has at least three people who have the right to release to PyPI.

Repository owners can rest assured that no ``tox-dev`` administrator will ever make
releases of your repository or take ownership in any way, except in rare cases
where someone becomes unresponsive after months of contact attempts.
As stated, the objective is to share maintenance and avoid "plugin-abandon".
