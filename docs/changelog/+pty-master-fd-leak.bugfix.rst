Close the pseudo-terminal master file descriptor when a command finishes running under a tty. It was never exposed as
a process stream, so it leaked on every executed command when tox was attached to a terminal, eventually exhausting
the process file-descriptor limit on large runs.
