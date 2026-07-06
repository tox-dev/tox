Report a clear error instead of crashing with ``IndexError`` when a ``deps`` or constraints entry is a bare
one-argument flag (``-c``, ``-r``, ``-f`` or ``-e``) with no value attached.
