Where descriptor-based ``rmtree`` and ``O_DIRECTORY``/``O_NOFOLLOW`` are available, clean environment, log, and
temporary directories relative to an open directory descriptor so a symlink swap cannot redirect deletions outside tox's
work directory. Replace a link already at the cleanup path without emptying its target.
