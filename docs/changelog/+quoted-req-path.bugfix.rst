On Windows, quoted option values in requirements files and ``deps``, such as ``-r "sub dir/base.txt"``, now have their
quotes removed as they do on other platforms and in pip; before, the quotes stayed in the path and the file could not be
opened. On every platform, a quoted ``-r``, ``-c`` or ``-f`` value in ``deps`` keeps its spaces as written instead of
gaining literal backslashes.
