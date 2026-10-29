Reject an entry separator supplied by a substitution within an INI list, set, dictionary or :ref:`env_list` entry. This
prevents a value inside one :ref:`requires` entry from adding a requirement, and a value inside one :ref:`env_list`
entry from selecting another environment. A substitution that occupies a whole entry can still expand to several
entries. The same check applies to text overrides supplied with ``-x`` or ``TOX_OVERRIDE``.
