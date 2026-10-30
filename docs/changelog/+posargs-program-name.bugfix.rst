When positional arguments supply the command, as in ``tox exec`` or ``commands = {posargs}``, tox now leaves a bare
program name such as ``python`` unchanged. It also leaves a bare executable first positional value unchanged, including
when a command uses that value as data, because wrappers can run it as a program. A same-named file in the start
directory no longer replaces the environment's program. An explicit path such as ``./python`` still follows
:ref:`args_are_paths`.
