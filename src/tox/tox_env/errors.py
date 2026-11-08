"""Defines tox error types."""

from __future__ import annotations


class Recreate(Exception):  # ruff:ignore[error-suffix-on-exception-name]  # public API name
    """Recreate the tox environment."""


class Skip(Exception):  # ruff:ignore[error-suffix-on-exception-name]  # public API name
    """Skip this tox environment."""


class Fail(Exception):  # ruff:ignore[error-suffix-on-exception-name]  # public API name
    """Failed creating env."""


class RunnerUnavailable(Exception):  # ruff:ignore[error-suffix-on-exception-name]  # public API name
    """Runner for this environment is not available."""


__all__ = [
    "Fail",
    "Recreate",
    "RunnerUnavailable",
    "Skip",
]
