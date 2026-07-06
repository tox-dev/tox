Fail evaluation gracefully instead of crashing the driver thread with ``ValueError: max_workers must be greater than
0`` when ``tox p -p all`` is run with an empty environment selection.
