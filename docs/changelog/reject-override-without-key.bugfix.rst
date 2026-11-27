Reject an override that has no key, such as ``-x =1``, instead of silently ignoring it. In ``TOX_OVERRIDE`` or the user
configuration file, such an entry now makes tox warn and ignore that list, as an entry without ``=`` already does.
