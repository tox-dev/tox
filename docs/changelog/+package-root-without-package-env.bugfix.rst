``pylock`` and ``dependency_groups`` now use ``package_root`` when a run has no package environment. They previously
used ``tox_root`` in that case.
