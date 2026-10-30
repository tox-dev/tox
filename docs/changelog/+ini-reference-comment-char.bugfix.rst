Preserve ``#`` in INI references to paths, so ``change_dir``, ``env_dir`` and ``set_env = file|...`` use the checkout
directory when its name contains ``#``. On POSIX, requirement-file paths with a space before ``#`` remain readable.
