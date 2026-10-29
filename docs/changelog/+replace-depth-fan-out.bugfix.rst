A host environment value selected by ``{env:NAME}`` that references itself twice could stall tox during recursive
expansion. tox now stops expansion at the first depth-limit hit, logs one warning, and leaves the remaining text
unexpanded.
