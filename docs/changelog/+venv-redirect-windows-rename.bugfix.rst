On Windows, tox pins the project path while reading or changing a ``.venv`` redirect. A concurrent directory rename or
junction added to an empty project directory cannot redirect a write or removal into another project. Redirect writes
replace ``.venv`` with a temporary file, leaving the target of a swapped ``.venv`` symlink or hard link unchanged.
