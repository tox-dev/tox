INI commands now keep a path reference such as ``{tox_root}``, ``{env_tmp_dir}`` or ``{env_python}`` within one
argument, including when the path contains spaces, quotes or backslashes. The same applies to tox-provided values such
as ``{host_python}`` and ``{tox_root_name}``, entries of a list such as ``{base_python}``, and file names matched by
``{glob:PATTERN}``. Command values set with ``-x`` or ``TOX_OVERRIDE`` follow the same rule.
