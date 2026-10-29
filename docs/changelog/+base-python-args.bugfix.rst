Pass each :ref:`base_python` entry to virtualenv as a separate ``--python`` argument. virtualenv split the old
``VIRTUALENV_PYTHON`` value on commas and ``os.pathsep``, then tried the first candidate last; that could start an
unintended program.
