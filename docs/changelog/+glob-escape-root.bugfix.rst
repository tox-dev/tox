Relative ``{glob:...}`` and TOML ``replace = "glob"`` patterns now match files when :ref:`tox_root` contains ``[``,
``*`` or ``?``. tox treats those characters in the project path literally while keeping wildcards in the configured
pattern.
