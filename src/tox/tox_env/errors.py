"""Defines tox error types."""

from __future__ import annotations


class Recreate(Exception):  # noqa: N818
    """Recreate the tox environment."""


class Skip(Exception):  # noqa: N818
    """Skip this tox environment."""


class Fail(Exception):  # noqa: N818
    """Failed creating env."""


class RunnerUnavailable(Exception):  # noqa: N818
    """Runner for this environment is not available."""
