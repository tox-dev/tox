``--result-json`` and ``tox config -o`` now create the parent directory of the output file when it does not exist; before,
tox crashed with a ``FileNotFoundError`` after the run and exited with ``1`` - by :user:`SulimanAbdulrazzaq`.
