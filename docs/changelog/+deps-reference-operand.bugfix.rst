INI commands that reference :ref:`deps` now preserve each pip option operand as one argument. A substituted
``--find-links`` path containing spaces can no longer add options to the command. The ``tox config`` display escapes
spaces, quotes and backslashes in those operands.
