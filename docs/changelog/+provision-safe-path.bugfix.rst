The provisioned tox now starts with Python's safe path option. During its ``-m tox`` re-exec, Python no longer puts the
start directory first on ``sys.path``, where an unrelated file could replace tox or a dependency.
