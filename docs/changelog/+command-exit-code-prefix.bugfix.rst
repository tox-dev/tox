``tox config`` and ``{[testenv:NAME]commands}`` references now keep the ``-`` and ``!`` exit-code prefixes of commands,
so an inherited ignored or inverted command no longer turns into a plain one.
