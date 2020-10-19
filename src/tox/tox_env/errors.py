"""Defines tox error types"""


class Recreate(RuntimeError):
    """Recreate the tox environment"""


class Skip(RuntimeError):
    """Skip this tox environment"""


class Fail(RuntimeError):
    """Failed creating env"""
