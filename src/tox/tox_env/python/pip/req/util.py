"""Borrowed from the pip code base."""  # simplint: ignore[catch-all-module]  # pip requirement parsing

from __future__ import annotations

from typing import Final
from urllib.parse import urlsplit
from urllib.request import url2pathname

from packaging.utils import canonicalize_name

VCS: Final[list[str]] = ["ftp", "ssh", "git", "hg", "bzr", "sftp", "svn"]
"""The names of the version control systems pip accepts in a requirement URL."""
_VALID_SCHEMAS: Final[list[str]] = [
    "http",
    "https",
    "file",
    *VCS,
]
"""The URL schemes a requirement can be given with."""


def is_url(name: str) -> bool:
    """Check whether a requirement name is a URL.

    :param name: the requirement name

    :returns: whether it is a URL

    """
    return get_url_scheme(name) in _VALID_SCHEMAS


def get_url_scheme(url: str) -> str | None:
    """Get the scheme of a URL, including the version control prefix.

    :param url: the requirement text to take the scheme from

    :returns: the scheme, or ``None`` when there is none

    """
    if ":" not in url:
        return None
    return url.split(":", 1)[0].lower()


def url_to_path(url: str) -> str:
    """Convert a ``file:`` URL to a path on the local file system.

    :param url: the ``file:`` URL to convert

    :returns: the path

    :raises ValueError: when the URL names a host other than the local machine

    """
    _, netloc, path, _, _ = urlsplit(url)
    if not netloc or netloc == "localhost":  # According to RFC 8089, same as empty authority.
        netloc = ""
    else:
        msg = f"non-local file URIs are not supported on this platform: {url!r}"
        raise ValueError(msg)
    return url2pathname(netloc + path)


def handle_binary_option(value: str, target: set[str], other: set[str]) -> None:
    """Apply the value of a binary option to the sets of packages it names.

    :param value: the comma separated names, where ``:all:`` selects every package and ``:none:`` clears the selection
    :param target: the set the named packages are added to
    :param other: the set the named packages are removed from

    """
    new = value.split(",")
    while ":all:" in new:
        other.clear()
        target.clear()
        target.add(":all:")
        del new[: new.index(":all:") + 1]
        if ":none:" not in new:
            return
    for name in new:
        if name == ":none:":
            target.clear()
            continue
        normalized_name = canonicalize_name(name)
        other.discard(normalized_name)
        target.add(normalized_name)


__all__ = [
    "VCS",
    "get_url_scheme",
    "handle_binary_option",
    "is_url",
    "url_to_path",
]
