A ``tox.toml`` or ``pyproject.toml`` string with literal braces around text containing a colon, such as a JSON argument
holding a URL or a time, is now kept as written, as in ``tox.ini``, instead of being read as a ``{key:default}``
reference. Positional arguments such as ``set_env:x`` passed into such braces through ``{posargs}`` no longer expand
into the value of that setting.
