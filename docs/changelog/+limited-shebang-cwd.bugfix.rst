On POSIX, tox now resolves relative commands and ``PATH`` entries from the command's working directory. The
``allowlist_externals`` check and ``TOX_LIMITED_SHEBANG`` interpreter selection use the file that the child executes.
