A relative ``{glob:...}`` pattern, or a TOML ``replace = "glob"`` table, now finds its files when the :ref:`tox_root`
path contains a ``[``, ``*`` or ``?``. Before, those characters were read as part of the pattern, so nothing matched and
the default was used.
