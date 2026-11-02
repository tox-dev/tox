PEP 723 metadata lines with content now require a space after ``#``. Empty blocks count when detecting duplicates, and
invalid ``requires-python`` values report a configuration error. Previously, malformed content lines could make tox read
metadata that other script runners ignored.
