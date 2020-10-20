"""
Apply value substitution (replacement) on tox strings.
"""
import os
import re
import sys
from configparser import SectionProxy
from typing import Callable, List, Optional, Tuple, Union

from tox.config.main import Config
from tox.config.sets import ConfigSet
from tox.execute.request import shell_cmd

BASE_TEST_ENV = "testenv"

ARGS_GROUP = re.compile(r"(?<!\\):")


def replace(
    value: str, conf: Optional[Config], name: Optional[str], section_loader: Callable[[str], Optional[SectionProxy]]
) -> str:
    while True:
        start, end, match = _find_replace_part(value)
        if not match:
            break
        replaced = _replace_match(conf, name, section_loader, value[start + 1 : end])
        new_value = value[:start] + replaced + value[end + 1 :]
        if new_value == value:  # if we're not making progress stop (circular reference?)
            break
        value = new_value
    return value


def _find_replace_part(value: str) -> Tuple[int, int, bool]:
    start, end, match = 0, 0, False
    while end != -1:
        end = value.find("}", end)
        if end == -1:
            continue
        if end > 1 and value[end - 1] == "\\":  # ignore escaped
            continue
        while start != -1:
            start = value.rfind("{", 0, end)
            if start > 1 and value[start - 1] == "\\":  # ignore escaped
                continue
            match = True
            break
        if match:
            break
    return start, end, match


def _replace_match(
    conf: Optional[Config],
    name: Optional[str],
    section_loader: Callable[[str], Optional[SectionProxy]],
    value: str,
) -> str:
    of_type, *args = ARGS_GROUP.split(value)
    if of_type == "env":
        replace_value = replace_env(args)
    elif of_type == "posargs":
        replace_value = replace_posarg(args)
    else:
        replace_value = replace_reference(conf, name, section_loader, value)
    if replace_value is None:
        return ""
    return str(replace_value)


_REPLACE_REF = re.compile(
    r"""
    (\[(testenv(:(?P<env>[^]]+))?|(?P<section>\w+))\])? # env/section
    (?P<key>[a-zA-Z0-9_]+) # key
    (:(?P<default>.*))? # default value
""",
    re.VERBOSE,
)


def replace_reference(
    conf: Optional[Config],
    name: Optional[str],
    section_loader: Callable[[str], Optional[SectionProxy]],
    value: str,
) -> str:
    match = _REPLACE_REF.match(value)
    if match:
        settings = match.groupdict()
        section = settings["env"] or settings["section"] or name
        if section is not None:
            if conf is not None and section in conf:
                section_conf: Union[None, ConfigSet, SectionProxy] = conf[section]
            elif conf is not None and section == "tox":
                section_conf = conf.core
            else:
                section_conf = section_loader(section)
            if section_conf is not None:
                key = settings["key"]
                try:
                    return str(section_conf[key])
                except Exception:  # noqa
                    default = settings["default"]
                    if default is not None:
                        return default
    return f"{{{value}}}"


def replace_posarg(args: List[str]) -> str:
    try:
        replace_value = shell_cmd(sys.argv[sys.argv.index("--") + 1 :])
    except ValueError:
        replace_value = args[0] if args else ""
    return replace_value


def replace_env(args: List[str]) -> str:
    key = args[0]
    default = "" if len(args) == 1 else args[1]
    return os.environ.get(key, default)
