Strip the backslash from an escaped semicolon (``\;``) in ``set_env`` values, so ``FOO=a\;b`` yields ``a;b`` instead
of leaking the backslash into the environment variable.
