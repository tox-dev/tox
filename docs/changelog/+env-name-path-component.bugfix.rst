tox now rejects environment names that are not a single path component before creating an environment. This prevents a
substituted ``env_list``, label or package environment name from selecting a directory outside ``work_dir``.
