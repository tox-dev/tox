"""Helpers for masking secret-looking content in user-facing logs."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence

# Based on the gitleaks ``generic-api-key`` rule. We err on the side of false positives because over-redaction is
# reversible by the user but a leaked secret is not. See https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml#L587
_SECRET_KEYWORDS: Final[tuple[str, ...]] = (
    "access",
    "api",
    "auth",
    "client",
    "cred",
    "key",
    "passwd",
    "password",
    "private",
    "pwd",
    "secret",
    "token",
)
_SECRET_ENV_VAR_REGEX: Final[re.Pattern[str]] = re.compile(
    r"""
    .*                  # any prefix
    ( {keywords} )      # one of the secret keywords
    .*                  # any suffix
    """.format(keywords="|".join(_SECRET_KEYWORDS)),
    re.VERBOSE | re.IGNORECASE,
)


def redact_value(name: str, value: str) -> str:
    """Mask ``value`` if ``name`` looks like it identifies a secret.

    :param name: the variable / option name to test against the secret keyword regex.
    :param value: the value associated with ``name``; replaced with asterisks of the same length on a match.

    :returns: ``value`` unchanged, or a string of ``*`` of the same length when ``name`` matches.

    """
    if _SECRET_ENV_VAR_REGEX.match(name):
        return "*" * len(value)
    return value


def redact_argv(argv: Sequence[str]) -> list[str]:
    """Return a copy of ``argv`` with secret-looking ``--key=value`` token values masked.

    Only the inline ``--key=value`` / ``-k=value`` form is detected. Space-separated arguments are left alone to avoid
    masking innocuous selectors like ``pytest -k test_foo``: there is no general way to tell ``--token <value>`` apart
    from ``--token <not-a-value>`` without per-tool knowledge of the parser.

    :param argv: the command line tokens to scan.

    :returns: a new list with values of secret-looking flags replaced by ``*`` of the same length.

    """
    result: list[str] = []
    for token in argv:
        if token.startswith("-") and "=" in token:
            flag, sep, value = token.partition("=")
            name = flag.lstrip("-")
            if _SECRET_ENV_VAR_REGEX.match(name):
                result.append(f"{flag}{sep}{'*' * len(value)}")
                continue
        result.append(token)
    return result


__all__ = (
    "redact_argv",
    "redact_value",
)
