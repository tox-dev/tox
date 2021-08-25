Development
===========

Getting started
---------------


``tox`` is a volunteer maintained open source project and we welcome contributions of all forms. The sections
below will help you get started with development, testing, and documentation. We’re pleased that you are interested in
working on tox. This document is meant to get you setup to work on tox and to act as a guide and reference
to the development setup. If you face any issues during this process, please
`open an issue <https://github.com/tox-dev/tox/issues/new?title=Trouble+with+development+environment>`_ about it on
the issue tracker.

Setup
~~~~~

tox is a command line application written in Python. To work on it, you'll need:

- **Source code**: available on `GitHub <https://github.com/tox-dev/tox>`_. You can use ``git`` to clone the
  repository:

  .. code-block:: shell

      git clone https://github.com/tox-dev/tox
      cd tox

- **Python interpreter**: We recommend using ``CPython``. You can use
  `this guide <https://realpython.com/installing-python/>`_ to set it up.

- :pypi:`tox`: to automatically get the projects development dependencies and run the test suite. We recommend
  installing it using `pipx <https://pipxproject.github.io/pipx/>`_.

Running from source tree
~~~~~~~~~~~~~~~~~~~~~~~~

The easiest way to do this is to generate the development tox environment, and then invoke tox from under the
``.tox/dev`` folder

.. code-block:: shell

    tox -e dev
    .tox/dev/bin/tox  # on Linux
    .tox/dev/Scripts/tox  # on Windows

Running tests
~~~~~~~~~~~~~

tox's tests are written using the :pypi:`pytest` test framework. :pypi:`tox` is used to automate the setup
and execution of tox's tests.

To run tests locally execute:

.. code-block:: shell

    tox -e py

This will run the test suite for the same Python version as under which ``tox`` is installed. Alternatively you can
specify a specific version of Python by using the ``pyNN`` format, such as: ``py38``, ``pypy3``, etc.

``tox`` has been configured to forward any additional arguments it is given to ``pytest``.
This enables the use of pytest's
`rich CLI <https://docs.pytest.org/en/latest/usage.html#specifying-tests-selecting-tests>`_. As an example, you can
select tests using the various ways that pytest provides:

.. code-block:: shell

    # Using markers
    tox -e py -- -m "not slow"
    # Using keywords
    tox -e py -- -k "test_extra"

Some tests require additional dependencies to be run, such is the various shell activators (``bash``, ``fish``,
``powershell``, etc). The tests will be skipped automatically if the dependencies are not present. Please note however that in CI
all tests are run; so even if all tests succeed locally for you, they may still fail in the CI.

Running linters
~~~~~~~~~~~~~~~

tox uses :pypi:`pre-commit` for managing linting of the codebase. ``pre-commit`` performs various checks on all
files in tox and uses tools that help following a consistent code style within the codebase. To use linters locally,
run:

.. code-block:: shell

    tox -e fix

.. note::

    Avoid using ``# noqa`` comments to suppress linter warnings - wherever possible, warnings should be fixed instead.
    ``# noqa`` comments are reserved for rare cases where the recommended style causes severe readability problems or
    sidestep bugs within the linters.

Code style guide
~~~~~~~~~~~~~~~~

- First and foremost, the linters configured for the project must pass; this generally means following PEP-8 rules,
  as codified by: ``flake8``, ``black``, ``isort``, ``pyupgrade``.
- The supported Python versions (and the code syntax to use) are listed in the ``setup.cfg`` file
  in the ``options/python_requires`` entry. However, there are some files that have to be kept compatible
  with Python 2.7 to allow and test for running Python 2 envs from tox. They are listed in ``.pre-commit-config.yaml``
  under ``repo: https://github.com/asottile/pyupgrade`` under ``hooks/exclude``.
  Please do not attempt to modernize them to Python 3.x.
- Packaging options should be specified within ``setup.cfg``; ``setup.py`` is only kept for editable installs.
- All code (tests too) must be type annotated as much as required by ``mypy``.
- We use a line length of 120.
- Exception messages should only be capitalized (and ended with a period/exclamation mark) if they are multi-sentenced,
  which should be avoided. Otherwise, use statements that start with lowercase.
- All function (including test) names must follow PEP-8, so they must be fully snake cased. All classes are upper
  camel-cased.
- Prefer f-strings instead of the ``str.format`` method.
- Tests should contain as little information as possible but do use descriptive variable names within it.

Building documentation
~~~~~~~~~~~~~~~~~~~~~~

tox's documentation is built using :pypi:`Sphinx`. The documentation is written in reStructuredText. To build it
locally, run:

.. code-block:: shell

    tox -e docs

The built documentation can be found in the ``.tox/docs_out`` folder and may be viewed by opening ``index.html`` within
that folder.

Release
~~~~~~~

tox's release schedule is tied to ``pip``, ``setuptools`` and ``wheel``. We bundle the latest version of these
libraries so each time there's a new version of any of these, there will be a new tox release shortly afterwards
(we usually wait just a few days to avoid pulling in any broken releases).

Contributing
-------------

Submitting pull requests
~~~~~~~~~~~~~~~~~~~~~~~~

Submit pull requests (PRs) against the ``master`` branch, providing a good description of what you're doing and why. You must
have legal permission to distribute any code you contribute to tox and it must be available under the MIT
License. Provide tests that cover your changes and run the tests locally first. tox
:ref:`supports <compatibility-requirements>` multiple Python versions and operating systems. Any pull request must
consider and work on all these platforms.

Pull requests should be small to facilitate review. Keep them self-contained, and limited in scope. `Studies have shown
<https://www.kessler.de/prd/smartbear/BestPracticesForPeerCodeReview.pdf>`_ that review quality falls off as patch size
grows. Sometimes this will result in many small PRs to land a single large feature. In particular, pull requests must
not be treated as "feature branches", with ongoing development work happening within the PR. Instead, the feature should
be broken up into smaller, independent parts which can be reviewed and merged individually.

Additionally, avoid including "cosmetic" changes to code that is unrelated to your change, as these make reviewing the
PR more difficult. Examples include re-flowing text in comments or documentation, or addition or removal of blank lines
or whitespace within lines. Such changes can be made separately, as a "formatting cleanup" PR, if needed.

Automated testing
~~~~~~~~~~~~~~~~~

All pull requests and merges to the ``master`` branch are tested using
`GitHub Actions <https://github.com/features/actions>`_ (configured by ``check.yml`` file inside the
``.github/workflows`` directory). You can find the status and the results to the CI runs for your
PR on GitHub's Web UI for the pull request. You can also find links to the CI services' pages for the specific builds in
the form of "Details" links, in case the CI run fails and you wish to view the output.

To trigger CI to run again for a pull request, you can close and open the pull request or submit another change to the
pull request. If needed, project maintainers can manually trigger a restart of a job/build.

Changelog entries
~~~~~~~~~~~~~~~~~

The ``changelog.rst`` file is managed using :pypi:`towncrier` and all changes must be accompanied by a
changelog entry. To add an entry to the changelog, first you need to have created an issue describing the
change you want to make. A  pull request itself *may* function as such, but it is preferred to have a dedicated issue
(for example, in case the PR ends up rejected due to code quality reasons).

There is no need to create an issue for trivial changes, e.g. for typo fixes.

Once you have an issue or pull request, you take the number and you create a file inside of the ``docs/changelog``
directory named after that issue number with an extension of:

- ``feature.rst``,
- ``bugfix.rst``,
- ``doc.rst``,
- ``removal.rst``,
- ``misc.rst``.

Thus if your issue or PR number is ``1234`` and this change is fixing a bug, then you would create a file
``docs/changelog/1234.bugfix.rst``. PRs can span multiple categories by creating multiple files (for instance, if you
added a feature and deprecated/removed the old feature at the same time, you would create
``docs/changelog/1234.bugfix.rst`` and ``docs/changelog/1234.remove.rst``). Likewise if a PR touches multiple issues/PRs
you may create a file for each of them with the same contents and :pypi:`towncrier` will deduplicate them.

Contents of a changelog entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The content of this file is reStructuredText formatted text that will be used as the content of the changelog entry.
You do not need to reference the issue or PR numbers here as towncrier will automatically add a reference to all of
the affected issues when rendering the changelog.

In order to maintain a consistent style in the ``changelog.rst`` file, it is preferred to keep the entries to the
point, in sentence case, shorter than 120 characters and in an imperative tone -- an entry should complete the sentence
``This change will …``. In rare cases, where one line is not enough, use a summary line in an imperative tone followed
by a blank line separating it from a description of the feature/change in one or more paragraphs, each wrapped
at 120 characters. Remember that a changelog entry is meant for end users and should only contain details relevant to an
end user.


Becoming a maintainer
~~~~~~~~~~~~~~~~~~~~~

If you want to become an official maintainer, start by helping out. As a first step, we welcome you to triage issues on
tox's issue tracker. tox maintainers provide triage abilities to contributors once they have been around
for some time and contributed positively to the project. This is optional and highly recommended for becoming a
tox maintainer. Later, when you think you're ready, get in touch with one of the maintainers and they will
initiate a vote among the existing maintainers.

.. note::

    Upon becoming a maintainer, a person should be given access to various tox-related tooling across
    multiple platforms. These are noted here for future reference by the maintainers:

    - GitHub Push Access
    - PyPI Publishing Access
    - CI Administration capabilities
    - ReadTheDocs Administration capabilities
    - The list below

.. _current-maintainers:

Current maintainers
^^^^^^^^^^^^^^^^^^^

-  `Anthony Sottile <https://github.com/asottile>`_
-  `Bernát Gábor <https://github.com/gaborbernat>`_
-  `Jürgen Gmach <https://github.com/jugmac00>`_
-  `Miroslav Šedivý <https://github.com/eumiro>`_
-  `Oliver Bestwalter <https://github.com/obestwalter>`_
