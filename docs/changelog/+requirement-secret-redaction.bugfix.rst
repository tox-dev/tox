Values expanded from secret-named environment variables in requirements files no longer appear in the install cache,
recreation warnings, or file-read errors. tox may recreate an existing environment once to replace a cache written by an
older version.
