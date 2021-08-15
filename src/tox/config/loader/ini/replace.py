"""
Apply value substitution (replacement) on tox strings.
"""
import os
import re
import sys
from configparser import SectionProxy
from pathlib import Path
from typing import TYPE_CHECKING, Iterator, List, Optional, Tuple, Union

from tox.config.loader.stringify import stringify
from tox.config.set_env import SetEnv
from tox.config.sets import ConfigSet
from tox.execute.request import shell_cmd

if TYPE_CHECKING:
    from tox.config.loader.ini import IniLoader
    from tox.config.main import Config

BASE_TEST_ENV = "testenv"

# split alongside :, unless it's escaped, or it's preceded by a single capital letter (Windows drive letter in paths)
ARGS_GROUP = re.compile(r"(?<!\\\\|:[A-Z]):")


def replace(conf: "Config", name: Optional[str], loader: "IniLoader", value: str, chain: List[str]) -> str:
    # perform all non-escaped replaces
    end = 0
    while True:
        start, end, to_replace = find_replace_part(value, end)
        if to_replace is None:
            break
        replaced = _replace_match(conf, name, loader, to_replace, chain.copy())
        if replaced is None:
            # if we cannot replace, keep what was there, and continue looking for additional replaces following
            # note, here we cannot raise because the content may be a factorial expression, and in those case we don't
            # want to enforce escaping curly braces, e.g. it should work to write: env_list = {py39,py38}-{,dep}
            end = end + 1
            continue
        new_value = value[:start] + replaced + value[end + 1 :]
        end = 0  # if we performed a replacement start over
        if new_value == value:  # if we're not making progress stop (circular reference?)
            break
        value = new_value
    # remove escape sequences
    value = value.replace("\\{", "{")
    value = value.replace("\\}", "}")
    value = value.replace("\\[", "[")
    value = value.replace("\\]", "]")
    return value


REPLACE_PART = re.compile(
    r"""
        (?<! \\) \{  # Unescaped {
            ( [^{}] | \\ \{ | \\ \} )*  # Anything except an unescaped { or }
        (?<! \\) \}  # Unescaped }
    |
        (?<! \\) \[ \]  # Unescaped []
    """,
    re.VERBOSE,
)  # simplified - not verbose version (?<!\\)([^{}]|\\\{|\\\})*(?<!\\)\}|(?<!\\)\[\]


def find_replace_part(value: str, end: int) -> Tuple[int, int, Optional[str]]:
    match = REPLACE_PART.search(value, end)
    if match is None:
        return -1, -1, None
    if match.group() == "[]":
        return match.start(), match.end() - 1, "posargs"  # brackets is an alias for positional arguments
    return match.start(), match.end() - 1, match.group()[1:-1]


def _replace_match(
    conf: "Config", current_env: Optional[str], loader: "IniLoader", value: str, chain: List[str]
) -> Optional[str]:
    of_type, *args = ARGS_GROUP.split(value)
    if of_type == "/":
        replace_value: Optional[str] = os.sep
    elif of_type == "" and args == [""]:
        replace_value = os.pathsep
    elif of_type == "env":
        replace_value = replace_env(conf, current_env, args, chain)
    elif of_type == "tty":
        replace_value = replace_tty(args)
    elif of_type == "posargs":
        replace_value = replace_pos_args(conf, current_env, args)
    else:
        replace_value = replace_reference(conf, current_env, loader, value, chain)
    return replace_value


_REPLACE_REF = re.compile(
    rf"""
    (\[(?P<full_env>{BASE_TEST_ENV}(:(?P<env>[^]]+))?|(?P<section>[-\w]+))\])? # env/section
    (?P<key>[a-zA-Z0-9_]+) # key
    (:(?P<default>.*))? # default value
""",
    re.VERBOSE,
)


def replace_reference(
    conf: "Config",
    current_env: Optional[str],
    loader: "IniLoader",
    value: str,
    chain: List[str],
) -> Optional[str]:
    # a return value of None indicates could not replace
    match = _REPLACE_REF.match(value)
    if match:
        settings = match.groupdict()

        key = settings["key"]
        if settings["section"] is None and settings["full_env"]:
            settings["section"] = settings["full_env"]

        exception: Optional[Exception] = None
        try:
            for src in _config_value_sources(settings["env"], settings["section"], current_env, conf, loader):
                try:
                    if isinstance(src, SectionProxy):
                        return loader.process_raw(conf, current_env, src[key])
                    value = src.load(key, chain)
                    as_str, _ = stringify(value)
                    as_str = as_str.replace("#", r"\#")  # escape comment characters as these will be stripped
                    return as_str
                except KeyError as exc:  # if fails, keep trying maybe another source can satisfy
                    exception = exc
        except Exception as exc:
            exception = exc
        if exception is not None:
            if isinstance(exception, KeyError):  # if the lookup failed replace - else keep
                default = settings["default"]
                if default is not None:
                    return default
                # we cannot raise here as that would mean users could not write factorials: depends = {py39,py38}-{,b}
            else:
                raise exception
    return None


def _config_value_sources(
    env: Optional[str],
    section: Optional[str],
    current_env: Optional[str],
    conf: "Config",
    loader: "IniLoader",
) -> Iterator[Union[SectionProxy, ConfigSet]]:
    # if we have an env name specified take only from there
    # config is None only when loading the global tox config file for the CLI arguments, in this case no replace works
    if env is not None:
        if env in conf:
            yield conf.get_env(env)
        else:
            raise KeyError(f"missing tox environment with name {env}")

    if section is None:
        # if no section specified perhaps it's an unregistered config:
        # 1. try first from core conf
        yield conf.core
        # 2. and then fallback to our own environment
        if current_env is not None:
            yield conf.get_env(current_env)
        return

    # if there's a section, special handle the core section under name tox
    if section == loader.core_prefix:
        yield conf.core  # try via registered configs
    value = loader.get_section(section)  # fallback to section
    if value is not None:
        yield value


def replace_pos_args(conf: "Config", env_name: Optional[str], args: List[str]) -> str:
    to_path: Optional[Path] = None
    if env_name is not None:  # pragma: no branch
        env_conf = conf.get_env(env_name)
        try:
            if env_conf["args_are_paths"]:  # pragma: no branch
                to_path = env_conf["change_dir"]
        except KeyError:
            pass
    pos_args = conf.pos_args(to_path)
    if pos_args is None:
        replace_value = ":".join(args)  # if we use the defaults join back remaining args
    else:
        replace_value = shell_cmd(pos_args)
    return replace_value


def replace_env(conf: "Config", env_name: Optional[str], args: List[str], chain: List[str]) -> str:
    key = args[0]
    new_key = f"env:{key}"

    if env_name is not None:  # on core no set env support # pragma: no branch
        if new_key not in chain:  # check if set env
            chain.append(new_key)
            env_conf = conf.get_env(env_name)
            set_env: SetEnv = env_conf["set_env"]
            if key in set_env:
                return set_env.load(key, chain)
        elif chain[-1] != new_key:  # if there's a chain but only self-refers than use os.environ
            raise ValueError(f"circular chain between set env {', '.join(i[4:] for i in chain[chain.index(new_key):])}")

    if key in os.environ:
        return os.environ[key]

    return "" if len(args) == 1 else args[1]


def replace_tty(args: List[str]) -> str:
    if sys.stdout.isatty():
        result = args[0] if len(args) > 0 else ""
    else:
        result = args[1] if len(args) > 1 else ""
    return result


__all__ = (
    "BASE_TEST_ENV",
    "replace",
    "find_replace_part",
)
