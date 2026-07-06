Compare canonicalized names when detecting self-referential (recursive) extras, so a package whose name is not
canonical (e.g. ``my_pkg`` referencing ``my-pkg[foo]``) still pulls in the referenced extra's dependencies.
