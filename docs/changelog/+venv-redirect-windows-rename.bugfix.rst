On Windows, tox holds the project directory open without delete sharing while it checks or changes a ``.venv`` redirect.
This blocks an ordinary directory rename during that operation. Redirect writes replace ``.venv`` with a temporary file,
leaving the target of a swapped ``.venv`` symlink or hard link unchanged.
