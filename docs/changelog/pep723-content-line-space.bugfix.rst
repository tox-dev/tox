A PEP 723 inline script metadata block is read only when every content line is a bare ``#`` or a ``#`` followed by a
space, which is what the specification requires. A ``#key = value`` line used to be accepted as metadata, so the same
script could resolve to one set of dependencies under the ``virtualenv-pep-723`` runner and to none under any other
PEP 723 runner.
