Plugin How-to Guides
====================

Extension points
-----------------

.. automodule:: tox.plugin
   :members:
   :exclude-members: impl

.. autodata:: tox.plugin.impl
   :no-value:

.. automodule:: tox.plugin.spec
   :members:

Adopting a plugin under the tox-dev organization
--------------------------------------------------

You're free to host your plugin on your favorite platform. However, the core tox development happens on GitHub under
the ``tox-dev`` organization. We are happy to adopt tox plugins under the ``tox-dev`` organization if:

- the plugin solves a valid use case and is not malicious,
- it's released on PyPI with at least 100 downloads per month (to ensure it's actively used).

What's in it for you:

- you get owner rights on the repository under the tox-dev organization,
- exposure of your plugin under the core umbrella,
- backup maintainers from other tox plugin developers.

How to apply:

- create an issue under the ``tox-dev/tox`` GitHub repository with the title
  :gh:`Adopt plugin \<name\> <login?return_to=https%3A%2F%2Fgithub.com%2Ftox-dev%2Ftox%2Fissues%2Fnew%3Flabels%3Dfeature%253Anew%26template%3Dfeature_request.md%26title%3DAdopt%2520plugin%26body%3D>`,
- wait for the green light by one of the maintainers (see :ref:`current-maintainers`),
- follow the `guidance by GitHub
  <https://docs.github.com/en/repositories/creating-and-managing-repositories/transferring-a-repository>`_,
- (optionally) add at least one other person as co-maintainer on PyPI.
