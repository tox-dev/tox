Stop a native TOML ``{ replace = "env" }`` substitution from leaking its resolution chain into sibling entries of the
same list, which made a value referencing the same environment variable twice (with another reference in between) fail
to load with a spurious ``circular chain`` error.
