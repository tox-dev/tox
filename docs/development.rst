#############
 Development
#############

.. toctree::
    :hidden:

    onboarding

************
 Key points
************

If you're already experienced with submitting GitHub PRs to open-source Python projects, the following are the key
points you need to know about this project. (If you're not, you should carefully read all the documentation after this
section. This section contains only highlights; it's not a substitute for reading this entire file.)

- Check the `style guide <#code-style-guide>`_ below. Note that ``tox -e fix`` will not catch the following:

  - Lines wrapped at less than 120 characters. Lines should be wrapped at 120 characters, not the PEP-8 standard of 79.
  - Variable names should be at least two characters long.

- Documentation is in `RST <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_ format; beware the
  differences from GitHub Markdown. The tox ``docs`` and ``fix`` targets will catch only some RST errors; documentation
  changes *must* be checked visually (see below).
- User-facing changes need a fragment in ``docs/changelog``. Use a descriptive filename with a category suffix, such as
  ``fix-windows-quoting.bugfix.rst``. Internal changes use the ``skip news`` label. See the `changelog entry
  <#changelog-entries>`_ guidance below.
- GitHub Actions will do a full set of `tests and checks <#automated-testing>`_ when the PR is submitted. For local
  testing you'll need to install your own "top-level" tox (using pipx_ or similar is fine) and use the following targets
  (tox environments):

  - :samp:`tox -e py [-- {pytest-arg ...}]` to `test code changes <#running-tests>`_.
  - ``tox -e type`` to typecheck changes. (All new code should have complete type annotations.)
  - ``tox -e docs`` to build documentation changes and update the changelog, followed by viewing (with a browser) the
    generated HTML files under :file:`.tox/docs_out/html/`. The required changelog entry can be viewed at the "Release
    History" link at the left.
  - ``tox -e fix`` to lint code, documentation and any other changes to the repo. This will also fix the code and write
    out the changed files; you can update your commit with ``git commit --amend``.

*****************
 Getting started
*****************

``tox`` is a volunteer maintained open source project and we welcome contributions of all forms. The sections below will
help you get started with development, testing, and documentation. We’re pleased that you are interested in working on
tox. This document is meant to get you setup to work on tox and to act as a guide and reference to the development
setup. If you face any issues during this process, please :issue:`open an issue
<new?title=Trouble+with+development+environment>` about it on the issue tracker.

Setup
=====

tox is a command line application written in Python. To work on it, you'll need:

- **Source code**: available on :gh_repo:`GitHub <tox-dev/tox>`. You can use ``git`` to clone the repository:

  .. code-block:: shell

      git clone https://github.com/tox-dev/tox
      cd tox

- **Python interpreter**: We recommend using ``CPython``. You can use `this guide
  <https://realpython.com/installing-python/>`_ to set it up.
- :pypi:`tox`: to automatically get the projects development dependencies and run the test suite. We recommend
  installing it using `pipx <https://pipxproject.github.io/pipx/>`_.

Running from source tree
========================

The easiest way to do this is to generate the development tox environment, and then invoke tox from under the
``.tox/dev`` folder

.. code-block:: shell

    tox -e dev
    .tox/dev/bin/tox  # on Linux
    .tox/dev/Scripts/tox  # on Windows

Running tests
=============

tox's tests are written using the :pypi:`pytest` test framework. :pypi:`tox` is used to automate the setup and execution
of tox's tests.

To run tests locally execute:

.. code-block:: shell

    tox -e py

The ``py`` environment runs the test suite on Python 3.15, as configured in :file:`tox.toml`. Select another supported
interpreter using its environment name, for example:

.. code-block:: shell

    tox -e 3.11
    tox -e 3.14

Run ``tox list`` to see the available test and development environments.

``tox`` has been configured to forward any additional arguments it is given to ``pytest``. This enables the use of
pytest's `rich CLI <https://docs.pytest.org/en/latest/how-to/usage.html#specifying-which-tests-to-run>`_. As an example,
you can select tests using the various ways that pytest provides:

.. code-block:: shell

    # Using markers
    tox -e py -- -m "not slow"
    # Using keywords
    tox -e py -- -k "test_extra"

Some tests require additional dependencies to be run, such is the various shell activators (``bash``, ``fish``,
``powershell``, etc). The tests will be skipped automatically if the dependencies are not present. Please note however
that in CI all tests are run; so even if all tests succeed locally for you, they may still fail in the CI.

Running linters
===============

tox uses :pypi:`pre-commit` for managing linting of the codebase. ``pre-commit`` performs various checks on all files in
tox and uses tools that help following a consistent code style within the codebase. To use linters locally, run:

.. code-block:: shell

    tox -e fix

.. note::

    Avoid using ``# noqa`` comments to suppress linter warnings - wherever possible, warnings should be fixed instead.
    ``# noqa`` comments are reserved for rare cases where the recommended style causes severe readability problems or
    sidestep bugs within the linters.

Code style guide
================

- First and foremost, the linters configured for the project must pass; this generally means following PEP-8 rules, as
  codified by ``ruff`` (which replaces the previously used ``flake8``, ``black``, ``isort``, and ``pyupgrade``).
- The supported Python versions (and the code syntax to use) are listed in the ``pyproject.toml`` file in the
  ``project/requires-python`` entry.
- All code (tests too) must be type annotated as much as required by ``mypy``.
- We use a line length of 120.
- Exception messages should only be capitalized (and ended with a period/exclamation mark) if they are multi-sentenced,
  which should be avoided. Otherwise, use statements that start with lowercase.
- All function (including test) names must follow PEP-8, so they must be fully snake cased. All classes are upper
  camel-cased.
- Prefer f-strings instead of the ``str.format`` method.
- Tests should contain as little information as possible but do use descriptive variable names within it.

Building documentation
======================

tox's documentation is built using :pypi:`Sphinx`. The documentation is written in reStructuredText. To build it
locally, run:

.. code-block:: shell

    tox -e docs

The built documentation can be found in the ``.tox/docs_out/html`` folder and may be viewed by opening ``index.html``
within that folder.

**************
 Contributing
**************

Submitting pull requests
========================

Submit pull requests (PRs) against the ``main`` branch, providing a good description of what you're doing and why. You
must have legal permission to distribute any code you contribute to tox and it must be available under the MIT License.
Provide tests that cover your changes and run the tests locally first. tox :ref:`supports <compatibility-requirements>`
multiple Python versions and operating systems. Any pull request must consider and work on all these platforms.

Pull requests should be small to facilitate review. Keep them self-contained, and limited in scope. Studies have shown
that review quality falls off as patch size grows. In particular, pull requests must not be treated as "feature
branches", with ongoing development work happening within the PR. Instead, the feature should be broken up into smaller,
independent parts which can be reviewed and merged individually.

Additionally, avoid including "cosmetic" changes to code that is unrelated to your change, as these make reviewing the
PR more difficult. Examples include re-flowing text in comments or documentation, or addition or removal of blank lines
or whitespace within lines. Such changes can be made separately, as a "formatting cleanup" PR, if needed.

Automated testing
=================

All pull requests and merges to the ``main`` branch are tested using :gh:`GitHub Actions <features/actions>` (configured
by ``check.yaml`` file inside the ``.github/workflows`` directory). You can find the status and the results to the CI
runs for your PR on GitHub's Web UI for the pull request. You can also find links to the CI services' pages for the
specific builds in the form of "Details" links, in case the CI run fails and you wish to view the output.

To trigger CI to run again for a pull request, you can close and open the pull request or submit another change to the
pull request. If needed, project maintainers can manually trigger a restart of a job/build.

Changelog entries
=================

The changelog records changes that affect users. Put one reStructuredText fragment in ``docs/changelog`` for each
user-facing change. The fragment can use a descriptive name, so you do not need an issue or PR number before writing it.
For example, ``docs/changelog/fix-windows-quoting.bugfix.rst``. A merged squash PR links its named fragments to the PR
number and credits its human authors. Do not add a ``by`` credit inside the fragment. If a PR needs more than one entry,
add more than one fragment.

Choose the category that describes the effect on users:

- ``feature`` (Added): new capabilities, including adding or dropping Python support;
- ``change`` (Changes): changes to existing behavior;
- ``bugfix`` (Fixed): corrections to existing behavior;
- ``doc`` (Documentation): guidance users need to use tox;
- ``breaking`` (Breaking changes): incompatible behavior in a new release;
- ``security`` (Security): fixes to a security issue;
- ``performance`` (Performance): user-visible speed or resource improvements;
- ``deprecation`` (Deprecated): behavior scheduled for removal;
- ``removal`` (Removed): removed user-facing capabilities;
- ``packaging`` (Packaging): distribution or installation changes.

A Python support change belongs in ``feature`` and leads to a minor release. Older releases remain available for
interpreters no longer supported by new releases. Changelog entries should explain the effect from a user's point of
view. Internal refactors, CI changes, and routine dependency updates do not need entries. Apply the ``skip news`` label
for those PRs; the label can be added after the PR opens. A bot PR gets that label automatically when it has no
fragment. A bot PR with a fragment is checked and included like any other PR.

The fragment is a short sentence in RST. For example:

.. code-block:: rst

    Preserve single and double quotes in Windows command arguments.

The PR check validates fragment names and contents. It checks a human PR for a fragment unless ``skip news`` is present.
Release preparation renders the fragments into this page, with permanent anchors for each version and nonempty category.

Becoming a maintainer
=====================

If you want to become an official maintainer, start by helping out. As a first step, we welcome you to triage issues on
tox's issue tracker. tox maintainers provide triage abilities to contributors once they have been around for some time
and contributed positively to the project. This is optional and highly recommended for becoming a tox maintainer. Later,
when you think you're ready, get in touch with one of the maintainers and they will initiate a vote among the existing
maintainers.

.. note::

    Upon becoming a maintainer, a person should be given access to various tox-related tooling across multiple
    platforms. These are noted here for future reference by the maintainers:

    - GitHub Push Access (provides also CI administration capabilities)
    - PyPI Publishing Access
    - ReadTheDocs Administration capabilities (the root domain `tox.wiki <https://tox.wiki/en/latest/>`_ is currently
      owned and maintained by the primary maintainer and author ``Bernat Gabor``; bought via `Porkbun
      <https://porkbun.com/>`_ -- reach out to him directly for any changes).

Creating a new release
======================

A maintainer dispatches `Prepare Release <https://github.com/tox-dev/tox/actions/workflows/prepare-release.yaml>`_ on
``main``. Choose ``auto`` unless there is a reason to force a major, minor, or patch bump. ``auto`` selects a minor
release when pending fragments include a feature and a patch release otherwise. The version comes from the current tags
and fragments; no one needs to type it.

The keyless jobs assemble the changelog, run ``prek`` on the release tree, and validate the resulting patch. A separate
job verifies the same patch before a repository-scoped GitHub App commits it and pushes the tag. The App's private key
lives in the ``release-auth`` environment, restricted to ``main``. The workflow uses no personal access token.

The tag starts ``release.yaml``. Its source check runs ``prek``; the build and notes jobs check the tagged changelog and
distribution. A separate job asks GitHub for contributor metadata. PyPI trusted publishing follows only after those jobs
pass. The final job creates or updates the GitHub Release with category headings, contributor credits, the PyPI link,
and the full changelog comparison.

To rehearse a release locally, use a disposable worktree with at least one pending fragment. The tag and commit stay
local; nothing is pushed or published. The release tools come from the same ``pylock.toml`` selection as CI:

.. code-block:: shell

    git worktree add --detach ../tox-release-preview HEAD
    cd ../tox-release-preview
    uv venv --python 3.15 .venv-release
    uv pip sync --preview-features pylock --python .venv-release/bin/python --group release pylock.toml
    tag=$(git tag --list | .venv-release/bin/release-creator tags --next auto --directory docs/changelog)
    .venv-release/bin/release-creator fragments --directory docs/changelog --repository tox-dev/tox --git --resolve-authors
    .venv-release/bin/towncrier build --yes --version "$tag"
    .venv-release/bin/prek run docstrfmt --files docs/changelog.rst
    .venv-release/bin/prek run --all-files
    git -c user.name='Release preview' -c user.email='release-preview@users.noreply.github.com' commit -am "Rehearse tox $tag"
    git tag "$tag"
    uv build --python 3.15 --out-dir dist
    .venv-release/bin/release-creator notes --changelog docs/changelog.rst --tag "$tag" --repository tox-dev/tox \
      --artifact-url "https://pypi.org/project/tox/$tag/"
    git tag -d "$tag"

The GitHub workflow also validates the release patch against the exact source commit. Remove the disposable worktree
after reviewing the package and notes.

.. _current-maintainers:

Current maintainers
-------------------

- :user:`Bernát Gábor <gaborbernat>`
- :user:`Jürgen Gmach <jugmac00>`
- :user:`Rahul Devikar <rahuldevikar>`

Previous maintainers
--------------------

- :user:`Anthony Sottile <asottile>`
- :user:`Masen Furer <masenf>`
- :user:`Oliver Bestwalter <obestwalter>`
