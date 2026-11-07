"""Defines tox error types."""

from __future__ import annotations


class Recreate(Exception):  # ruff:ignore[error-suffix-on-exception-name]
    """Recreate the tox environment."""


class Skip(Exception):  # ruff:ignore[error-suffix-on-exception-name]
    """Skip this tox environment."""


class Fail(Exception):  # ruff:ignore[error-suffix-on-exception-name]
    """Failed creating env."""


class RunnerUnavailable(Exception):  # ruff:ignore[error-suffix-on-exception-name]
    """Runner for this environment is not available."""
