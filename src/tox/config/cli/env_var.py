"""Provides configuration values from the environment variables."""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Any

from tox.config.loader.str_convert import StrConvert
from tox.util.redact import redact_argv

if TYPE_CHECKING:
    from types import UnionType

CONVERT = StrConvert()


def get_env_var(key: str, of_type: type[Any] | UnionType) -> tuple[Any, str] | None:
    """Get the environment variable option.

    :param key: the config key requested
    :param of_type: the type we would like to convert it to

    :returns: the converted value and its origin, or ``None`` if not found

    """
    key_upper = key.upper()
    for environ_key in (f"TOX_{key_upper}", f"TOX{key_upper}"):
        if environ_key in os.environ:
            value = os.environ[environ_key]
            origin = getattr(of_type, "__origin__", of_type.__class__)
            try:
                if origin is list:
                    entry_type = of_type.__args__[0]
                    result = [CONVERT.to(raw=v, of_type=entry_type, factory=None) for v in value.split(";") if v]
                else:
                    result = CONVERT.to(raw=value, of_type=of_type, factory=None)
            except Exception as exception:  # ruff:ignore[blind-except]
                # a flag can follow a ``;`` separator because TOX_OVERRIDE lists overrides that way. Mask entry by
                # entry first, so a secret that carries whitespace is masked whole instead of up to its first space,
                # then mask within the remaining whitespace-separated tokens.
                masked = ";".join(redact_argv(value.split(";")))
                redacted_value = "".join(redact_argv(re.split(r"(\s+|;)", masked)))
                # the exception text repeats the value it failed on
                reason = repr(exception).replace(value, redacted_value)
                logging.warning(
                    "env var %s=%r cannot be transformed to %r because %s",
                    environ_key,
                    redacted_value,
                    of_type,
                    reason,
                )
            else:
                return result, f"env var {environ_key}"
    return None


__all__ = [
    "get_env_var",
]
