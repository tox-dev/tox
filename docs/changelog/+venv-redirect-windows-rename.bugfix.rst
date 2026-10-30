On Windows, tox holds every directory in the project path open without delete sharing while it checks or changes a
``.venv`` redirect. This blocks ordinary directory renames and rejects a parent directory symlink. Redirect writes
replace ``.venv`` with a temporary file, leaving the target of a swapped ``.venv`` symlink or hard link unchanged.
