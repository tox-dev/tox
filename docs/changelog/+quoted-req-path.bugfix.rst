Quoted option values in requirements files and ``deps``, such as ``-r "sub dir/base.txt"``, now lose their quotes on
Windows like they do on other platforms and in pip, instead of keeping the quotes as part of the path. A quoted ``-r``,
``-c`` or ``-f`` value in ``deps`` also keeps its spaces as written instead of gaining literal backslashes.
