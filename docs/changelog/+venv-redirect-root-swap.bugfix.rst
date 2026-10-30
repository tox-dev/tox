On POSIX, tox now pins each directory on the path to the project root while reading or changing a ``.venv`` redirect. A
concurrent path swap can no longer redirect removal or replacement into another directory.
