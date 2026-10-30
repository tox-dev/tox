On Windows, INI command references such as ``{[testenv:a]commands}`` now preserve argument boundaries when a positional
argument contains an apostrophe or backslash. ``tox config`` displays the command with the same quoting tox uses to
parse a reference.
