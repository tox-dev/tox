Overview
========
This section contains system level information about tox.

Environment variables
---------------------
tox will inject the following environment variables that you can use to test that your command is running within tox:

.. versionadded:: 3.1

- ``TOX_WORK_DIR`` env var is set to the tox work directory
- ``TOX_ENV_NAME`` is set to the current running tox environment name
- ``TOX_ENV_DIR`` is set to the current tox environments working dir.
