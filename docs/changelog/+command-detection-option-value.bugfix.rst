Stop treating an option's value as the subcommand during command auto-detection, so selecting an environment whose
name matches a subcommand (e.g. ``tox -e list``) no longer fails with ``unrecognized arguments: -e``.
