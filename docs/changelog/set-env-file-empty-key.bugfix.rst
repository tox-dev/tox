A ``set_env`` line with an empty name, such as ``=value``, in ``tox.ini`` or in an environment file, now fails as an
invalid line instead of passing an unnamed variable to the commands, which broke them on Windows.
