"""Defines tox error types"""


class Recreate(Exception):  # noqa: N818
    """Recreate the tox environment"""


class Skip(Exception):  # noqa: N818
    """Skip this tox environment"""


class Fail(Exception):  # noqa: N818
    """Failed creating env"""
