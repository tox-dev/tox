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
_INLINE_FLAG_REGEX: Final[re.Pattern[str]] = re.compile(
    r"""
    (?<! [^\s'"=;] )          # not after a word character, quote, equals sign, or semicolon
    -                         # the dash that starts the flag
    (?: [^\s'"=] | [\r\n] )*  # the flag name, which may span line breaks in a fused token
    =                         # the equals sign that ends the flag
    """,
    re.VERBOSE,
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
    """Redact the secrets in the command line arguments, such as the passwords in URLs.

    :param argv: the command line arguments

    :returns: the arguments with the secrets replaced

    """
    result: list[str] = []
    for token in argv:
        redacted_token: str = _redact_url_userinfo(token)
        for match in _INLINE_FLAG_REGEX.finditer(redacted_token):
            if _SECRET_ENV_VAR_REGEX.match(match.group()):
                # A fused token has no reliable flag-value boundary.
                result.append(f"{redacted_token[: match.end()]}{'*' * (len(redacted_token) - match.end())}")
                break
        else:
            result.append(redacted_token)
    return result


def _redact_url_userinfo(token: str) -> str:
    return _REDACT_URL_USERINFO_PATTERN.sub(lambda match: f"{match['scheme']}{'*' * len(match['userinfo'])}@", token)


_REDACT_URL_USERINFO_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
        (?P<scheme> [a-zA-Z] [a-zA-Z0-9+.-]* :// )  # the URL scheme
        (?P<userinfo> [^/?#\s]+ )                    # the user and password before the host
        @                                            # the separator before the host
        """,
    flags=re.VERBOSE,
)


__all__ = [
    "redact_argv",
    "redact_value",
]
