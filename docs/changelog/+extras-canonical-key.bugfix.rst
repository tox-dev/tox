Canonicalize ``project.optional-dependencies`` keys when statically resolving extras, so a non-canonical key such as
``Foo_Bar`` still matches a requested ``foo-bar`` extra instead of silently dropping its dependencies.
