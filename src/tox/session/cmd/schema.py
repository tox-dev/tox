"""Generate schema for tox configuration, respecting the current plugins."""

from __future__ import annotations

import json
import sys
import typing
from pathlib import Path
from typing import TYPE_CHECKING

import packaging.requirements
import packaging.version

import tox.config.set_env
import tox.config.types
import tox.tox_env.python.pip.req_file
from tox.config.cli.parser import CORE
from tox.plugin import impl

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.config.sets import ConfigSet
    from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    our = parser.add_command(
        "schema", [], "Generate schema for tox configuration", gen_schema, inherit=frozenset({CORE})
    )
    our.add_argument("--strict", action="store_true", help="Disallow extra properties in configuration")


def gen_schema(state: State) -> int:
    core = state.conf.core
    strict = state.conf.options.strict

    # Use any available run environment for introspection (fall back to "py" which is always defined)
    env_name = next(state.envs.iter(only_active=False), "py")
    env_properties = _get_schema(state.envs[env_name].conf, path="#/properties/env_run_base/properties")

    properties = _get_schema(core, path="#/properties")

    # This accesses plugins that register new sections (like tox-gh)
    # Accessing a private member since this is not exposed yet and the
    # interface includes the internal storage tuple
    sections = {
        key: conf
        for s, conf in state.conf._key_to_conf_set.items()  # noqa: SLF001
        if (key := s[0].split(".")[0]) not in {"env_run_base", "env_pkg_base", "env"}
    }
    for key, conf in sections.items():
        properties[key] = {
            "type": "object",
            "additionalProperties": not strict,
            "properties": _get_schema(conf, path=f"#/properties/{key}/properties"),
        }

    docs_base = "https://tox.wiki/en/stable"
    json_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://raw.githubusercontent.com/tox-dev/tox/main/src/tox/tox.schema.json",
        "title": "tox configuration",
        "description": "tox configuration file (tox.toml or [tool.tox] in pyproject.toml)",
        "x-taplo": {"links": {"key": f"{docs_base}/config.html"}},
        "type": "object",
        "properties": {
            **properties,
            "env_run_base": {
                "type": "object",
                "description": "base configuration for run environments",
                "x-taplo": {"links": {"key": f"{docs_base}/config.html#run-environment"}},
                "properties": env_properties,
                "additionalProperties": not strict,
            },
            "env_pkg_base": {
                "type": "object",
                "$ref": "#/properties/env_run_base",
                "description": "base configuration for packaging environments",
                "x-taplo": {"links": {"key": f"{docs_base}/config.html#packaging-environment"}},
                "additionalProperties": not strict,
            },
            "env": {
                "type": "object",
                "description": "per-environment overrides (keyed by environment name)",
                "x-taplo": {"links": {"key": f"{docs_base}/config.html#run-environment"}},
                "patternProperties": {"^.*$": {"$ref": "#/properties/env_run_base"}},
            },
            "legacy_tox_ini": {
                "type": "string",
                "description": "tox configuration in INI format embedded in a TOML file",
                "x-taplo": {"links": {"key": f"{docs_base}/config.html#pyproject-toml-ini"}},
            },
        },
        "additionalProperties": not strict,
        "definitions": {
            "subs": {
                "anyOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "properties": {
                            "replace": {"type": "string"},
                            "name": {"type": "string"},
                            "default": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"$ref": "#/definitions/subs"}},
                                ]
                            },
                            "extend": {"type": "boolean"},
                        },
                        "required": ["replace"],
                        "additionalProperties": False,
                    },
                    {
                        "type": "object",
                        "properties": {
                            "replace": {"type": "string"},
                            "of": {"type": "array", "items": {"type": "string"}},
                            "default": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"$ref": "#/definitions/subs"}},
                                ]
                            },
                            "extend": {"type": "boolean"},
                        },
                        "required": ["replace", "of"],
                        "additionalProperties": False,
                    },
                ],
            },
        },
    }
    print(json.dumps(json_schema, indent=2))  # noqa: T201
    return 0


def _get_schema(conf: ConfigSet, path: str) -> dict[str, dict[str, typing.Any]]:
    properties: dict[str, dict[str, typing.Any]] = {}
    for x in conf.get_configs():
        name, *aliases = x.keys
        if (of_type := getattr(x, "of_type", None)) is None:
            continue
        desc = getattr(x, "desc", None)
        try:
            properties[name] = {**_process_type(of_type), "description": desc}
        except ValueError:
            print(name, "has unrecoginsed type:", of_type, file=sys.stderr)  # noqa: T201
        for alias in aliases:
            properties[alias] = {
                "$ref": f"{path}/{name}",
                "description": f"Deprecated: use {name!r} instead",
                "deprecated": True,
            }
    return properties


def _process_type(of_type: typing.Any) -> dict[str, typing.Any]:  # noqa: C901, PLR0911, PLR0912
    if of_type in {
        Path,
        str,
        packaging.version.Version,
        packaging.requirements.Requirement,
        tox.tox_env.python.pip.req_file.PythonDeps,
        tox.tox_env.python.pip.req_file.PythonConstraints,
    }:
        return {"type": "string"}
    if typing.get_origin(of_type) is typing.Union:
        types = [x for x in typing.get_args(of_type) if x is not type(None)]
        if len(types) == 1:
            return _process_type(types[0])
        msg = f"Union types are not supported: {of_type}"
        raise ValueError(msg)
    if of_type is bool:
        return {"type": "boolean"}
    if of_type is int:
        return {"type": "integer", "minimum": 0}
    if of_type is float:
        return {"type": "number"}
    if typing.get_origin(of_type) is typing.Literal:
        return {"enum": list(typing.get_args(of_type))}
    if of_type is tox.config.types.EnvList:
        return {
            "type": "array",
            "items": {
                "oneOf": [
                    {"$ref": "#/definitions/subs"},
                    {
                        "type": "object",
                        "required": ["product"],
                        "properties": {
                            "product": {
                                "type": "array",
                                "items": {
                                    "oneOf": [
                                        {"type": "array", "items": {"type": "string"}},
                                        {
                                            "type": "object",
                                            "required": ["prefix"],
                                            "properties": {
                                                "prefix": {"type": "string"},
                                                "start": {"type": "integer"},
                                                "stop": {"type": "integer"},
                                            },
                                            "additionalProperties": False,
                                        },
                                    ],
                                },
                                "description": "factor groups for cartesian product expansion",
                            },
                            "exclude": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "environment names to exclude from product",
                            },
                        },
                        "additionalProperties": False,
                    },
                ],
            },
        }
    if of_type is tox.config.types.Command:
        return {"type": "array", "items": {"$ref": "#/definitions/subs"}}
    if typing.get_origin(of_type) in {list, set}:
        if typing.get_args(of_type)[0] in {str, packaging.requirements.Requirement}:
            return {"type": "array", "items": {"$ref": "#/definitions/subs"}}
        if typing.get_args(of_type)[0] is tox.config.types.Command:
            return {"type": "array", "items": _process_type(typing.get_args(of_type)[0])}
        msg = f"Unknown list type: {of_type}"
        raise ValueError(msg)
    if of_type is tox.config.set_env.SetEnv:
        return {
            "type": "object",
            "additionalProperties": {"$ref": "#/definitions/subs"},
        }
    if typing.get_origin(of_type) is dict:
        return {
            "type": "object",
            "additionalProperties": {**_process_type(typing.get_args(of_type)[1])},
        }
    msg = f"Unknown type: {of_type}"
    raise ValueError(msg)
