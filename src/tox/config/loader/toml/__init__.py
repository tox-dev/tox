from __future__ import annotations

from tox.config.loader.api import ConfigLoadArgs, Loader, Override
from tox.config.loader.replacer import (
    MatchExpression,
    MatchRecursionError,
    RequirementLineCallbacks,
    replace,
    replace_command_lines,
    replace_for,
    replace_once,
    replace_requirement_lines,
)
from tox.config.loader.str_convert import StrConvert
from tox.config.set_env import SetEnv
from tox.config.types import CircularChainError, Command, EnvList
from tox.report import HandledError
from tox.tox_env.python.pip.req.file import protect_env_variables
from tox.tox_env.python.pip.req_file import PythonConstraints, PythonDeps
from tox.util.typing_compat import override

from ._api import TomlTypes
from ._replace import TomlReplaceLoader, Unroll
from ._validate import validate
from .loader import TomlLoader

__all__ = [
    "CircularChainError",
    "Command",
    "ConfigLoadArgs",
    "EnvList",
    "HandledError",
    "Loader",
    "MatchExpression",
    "MatchRecursionError",
    "Override",
    "PythonConstraints",
    "PythonDeps",
    "RequirementLineCallbacks",
    "SetEnv",
    "StrConvert",
    "TomlLoader",
    "TomlReplaceLoader",
    "TomlTypes",
    "Unroll",
    "override",
    "protect_env_variables",
    "replace",
    "replace_command_lines",
    "replace_for",
    "replace_once",
    "replace_requirement_lines",
    "validate",
]
