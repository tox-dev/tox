Render ``--no-binary`` and ``--only-binary`` from requirements files as comma-joined strings instead of leaking the
internal ``set`` object into the pip command line, which previously reached the subprocess as a non-string argument.
