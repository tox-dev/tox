"""Helpers for masking secret-looking content in user-facing logs."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence

# Based on the gitleaks ``generic-api-key`` rule. We err on the side of false positives because over-redaction is
# reversible by the user but a leaked secret is not.
# See https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml#L587
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
    re.VERBOSE | re.IGNORECASE | re.DOTALL,  # a newline before a keyword must not expose its value
)
# Compile once for command logging; broken quotes, semicolons, and line breaks can fuse flags into one token.
_INLINE_FLAG_REGEX: Final[re.Pattern[str]] = re.compile(r"""(?<![^\s'"=;])-(?:[^\s'"=]|[\r\n])*=""")


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
    result: list[str] = []
    for token in argv:
        for match in _INLINE_FLAG_REGEX.finditer(token):
            if _SECRET_ENV_VAR_REGEX.match(match.group()):
                # A fused token has no reliable flag-value boundary.
                result.append(f"{token[: match.end()]}{'*' * (len(token) - match.end())}")
                break
        else:
            result.append(token)
    return result


__all__ = [
    "redact_argv",
    "redact_value",
]
