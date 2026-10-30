Keep a substitution within the quoted INI command argument it is part of: ``"--title={env:TITLE}"`` is one argument even
when the value of ``TITLE`` holds quotes or whitespace, as it is for a TOML argument array. tox used to paste the value
into the command text before splitting it, so a quote in the value ended the argument and the rest of the value arrived
as further arguments of the command. ``install_command`` and ``list_dependencies_command`` get the same handling.
