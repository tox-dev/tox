Pass positional arguments, ``{glob:PATTERN}`` matches and ``TOX_FACTOR_<label>`` overrides through literally in INI
configuration: a ``{...}`` or ``[]`` in them is no longer substituted again, so ``tox run -- '{env:SECRET}'`` hands the
command ``{env:SECRET}`` instead of the variable's value and ``tox run -- '{posargs} -x'`` stays one argument. The
``DEFAULTS`` of ``{posargs:DEFAULTS}`` and referenced keys still expand their own substitutions.
