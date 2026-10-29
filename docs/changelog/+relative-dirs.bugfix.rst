tox now resolves relative ``env_dir``, ``env_tmp_dir``, ``env_log_dir``, ``work_dir``, ``temp_dir``, ``package_root``,
``meta_dir``, ``pkg_dir`` and ``package_glob`` values against :ref:`tox_root`. With ``tox -c path/to/tox.ini`` started
elsewhere, it no longer clears or reuses those directories in the start directory or selects a package from there.
