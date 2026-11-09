``{factor:label}`` now resolves to the factor the label's group put in the environment name when two groups share a
value. Before, with ``factors = [{ source = ["py312", "py313"] }, { target = ["py312", "py313"] }]``, the environment
``migrate-py313-py312`` read ``py312`` for both labels.
