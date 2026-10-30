``pylock`` and ``dependency_groups`` now resolve against the configured ``package_root`` even when no package
environment is created, instead of silently falling back to ``tox_root``.
