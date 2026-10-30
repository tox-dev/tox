An option that takes multiple values (``-f``, ``-m``, ``--discover``) now keeps every value ``argparse`` would
consume, so a later value that names a sub-command is no longer read as the command: ``tox -f py legacy`` ran the
environments matching ``py`` alone. Put the command before such an option.
