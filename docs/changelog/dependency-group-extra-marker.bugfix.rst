A dependency group entry that refers to the project's own extra with an environment marker, such as
``demo[dev]; python_version < "3.10"``, now keeps that marker on the extra's requirements instead of installing them
on every interpreter.
