tox now treats a Windows junction where a run environment's directory, or its ``log`` or ``tmp`` folder, should live as
it treats a symlink: it replaces the junction without touching the files of its target, also when the target is missing.
A junction at the environment directory itself makes tox fail with ``is a link where this environment should live``
unless ``-r`` is given, instead of raising ``FileExistsError``.
