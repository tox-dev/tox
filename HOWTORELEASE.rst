==================
How to release tox
==================

This matches the current model that can be summarized as this:

* tox has no long lived branches.

* Pull requests get integrated into master by members of the project when they feel confident that this could be part of the next release. Small fix ups might be done right after merge instead of discussing back and forth to get minor problems fixed, to keep the workflow simple.


**Normal releases**: done from master when enough changes have accumulated (whatever that means at any given point in time).

**"Special" releases**: (in seldom cases when master has moved on and is not in a state where a quick release should be done from that state): the current release tag is checked out, the necessary fixes are cherry picked and a package with a patch release increase is built from that state. This is not very clean but seems good enough at the moment as it does not happen very often. If it does happen more often, this needs some rethinking (and rather into the direction of making less buggy releases than complicating release development/release process).

HOWTO
=====

Prerequisites
-------------

* Push and merge rights for https://github.com/tox-dev/tox, also referred to as the *upstream*.
* A UNIX system that has:

  - ``tox``
  - ``git`` able to push to upstream

* Accountability: if you cut a release that breaks the CI builds of projects using tox, you are expected to fix this within a reasonable time frame (hours/days - not weeks/months) - if you don't feel quite capable of doing this yet, partner up with a more experienced member of the team and make sure they got your back if things break.

Release
-------
Run the release command and make sure you pass in the desired release number:

.. code-block:: bash

    tox -e release -- <version>

Create a pull request and wait until it the CI passes. Now make sure you merge the PR
and delete the release branch. The CI will automatically pick the tag up and
release it, wait to appear in PyPI. Only merge if the later happens.

Post release activities
-----------------------

Make sure to let the world know that a new version is out by whatever means you see fit.

As a minimum, send out a mail notification by triggering the notify tox environment:


.. code-block:: bash

    TOX_DEV_GOOGLE_SECRET=our_secret tox -e notify

Note you'll need the ``TOX_DEV_GOOGLE_SECRET`` key, what you can acquire from other maintainers.
