"""
Provides configuration values from the the environment variables.
"""
import logging
import os
from typing import Any, Optional, Tuple, Type

from tox.config.loader.str_convert import StrConvert

CONVERT = StrConvert()


def get_env_var(key: str, of_type: Type[Any]) -> Optional[Tuple[Any, str]]:
    """Get the environment variable option.

    :param key: the config key requested
    :param of_type: the type we would like to convert it to
    :return:
    """
    key_upper = key.upper()
    for fmt in ("TOX_{}", "TOX{}"):
        environ_key = fmt.format(key_upper)
        if environ_key in os.environ:
            value = os.environ[environ_key]
            try:
                source = f"env var {environ_key}"
                result = CONVERT.to(raw=value, of_type=of_type)
                return result, source
            except Exception as exception:  # noqa
                logging.warning(
                    "env var %s=%r cannot be transformed to %r because %r",
                    environ_key,
                    value,
                    of_type,
                    exception,
                )
    return None


__all__ = ("get_env_var",)
