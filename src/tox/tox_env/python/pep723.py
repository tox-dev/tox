"""PEP 723 inline script metadata support — shared logic for any venv backend."""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, cast

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from tox.config.types import Command
from tox.tox_env.errors import Fail
from tox.tox_env.python.pip.req_file import PythonDeps
from tox.tox_env.python.runner import add_skip_missing_interpreters_to_core, add_skip_missing_interpreters_to_env
from tox.tox_env.runner import RunToxEnv

from .api import Python

if sys.version_info >= (3, 11):  # pragma: >=3.11 cover
    import tomllib
else:  # pragma: <3.11 cover
    import tomli as tomllib

if TYPE_CHECKING:
    from pathlib import Path

    from tox.config.main import Config
    from tox.config.of_type import ConfigDynamicDefinition
    from tox.tox_env.api import ToxEnvCreateArgs

_SCRIPT_METADATA_RE: Final = re.compile(
    r"""
    (?m)
    ^[#][ ]///[ ](?P<type>[a-zA-Z0-9-]+)$  # opening: # /// <type>
    \s                                      # blank line or whitespace
    (?P<content>                            # TOML content lines:
        (?:^[#](?:| .*)$\s)+               #   each line starts with # (optionally followed by space + text)
    )
    ^[#][ ]///$                             # closing: # ///
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class ScriptMetadata:
    requires_python: str | None = None
    dependencies: list[str] = field(default_factory=list)


class Pep723Mixin(Python, RunToxEnv):
    """Mixin providing PEP 723 script metadata support for any venv-backed runner.

    Concrete runners compose this with a venv backend (VirtualEnv, UvVenv, etc.) and RunToxEnv.

    """

    _script_metadata: ScriptMetadata | None

    def __init__(self, create_args: ToxEnvCreateArgs) -> None:
        self._script_metadata = None
        super().__init__(create_args)

    def register_config(self) -> None:
        super().register_config()
        self.conf.add_config(
            keys=["script"],
            of_type=str,
            default="",
            desc="path to Python script with PEP 723 inline metadata (relative to tox_root)",
        )

        def default_commands(conf: Config, env_name: str | None) -> list[Command]:  # noqa: ARG001
            if script := self.conf["script"]:
                tox_root: Path = self.core["tox_root"]
                args = ["python", str(tox_root / script)]
                if (pos_args := conf.pos_args(None)) is not None:
                    args.extend(pos_args)
                return [Command(args)]
            return []

        commands_def = cast("ConfigDynamicDefinition[list[Command]]", self.conf._defined["commands"])  # noqa: SLF001
        commands_def.default = default_commands
        add_skip_missing_interpreters_to_core(self.core, self.options)
        add_skip_missing_interpreters_to_env(self.conf, self.core, self.options)

    def _setup_env(self) -> None:
        super()._setup_env()
        if self._base_python_explicitly_set:
            msg = "cannot set base_python with virtualenv-pep-723 runner; use requires-python in the script"
            raise Fail(msg)
        if script := self.conf["script"]:
            tox_root: Path = self.core["tox_root"]
            if not (tox_root / script).is_file():
                msg = f"script file not found: {tox_root / script}"
                raise Fail(msg)
        metadata = self._get_script_metadata()
        if metadata.requires_python:
            info = self.base_python
            py_version = Version(f"{info.version_info.major}.{info.version_info.minor}.{info.version_info.micro}")
            if py_version not in SpecifierSet(metadata.requires_python):
                msg = f"python {py_version} does not satisfy requires-python {metadata.requires_python!r}"
                raise Fail(msg)
        if getattr(self.options, "skip_env_install", False):
            logging.warning("skip installing dependencies")
            return
        if metadata.dependencies:
            root: Path = self.core["tox_root"]
            requirements = PythonDeps(metadata.dependencies, root)
            self._install(requirements, type(self).__name__, "deps")

    def _get_script_metadata(self) -> ScriptMetadata:
        if self._script_metadata is None:
            if not (script := self.conf["script"]):
                self._script_metadata = ScriptMetadata()
                return self._script_metadata
            tox_root: Path = self.core["tox_root"]
            full_path = tox_root / script
            if not full_path.is_file():
                self._script_metadata = ScriptMetadata()
                return self._script_metadata
            self._script_metadata = _parse_script_metadata(full_path.read_text(encoding="utf-8"))
        return self._script_metadata


def _parse_script_metadata(script: str) -> ScriptMetadata:
    blocks = [(m.group("type"), m.group("content")) for m in _SCRIPT_METADATA_RE.finditer(script)]
    script_blocks = [(t, c) for t, c in blocks if t == "script"]
    if len(script_blocks) > 1:
        msg = "multiple [script] metadata blocks found in script"
        raise ValueError(msg)
    if not script_blocks:
        return ScriptMetadata()
    content = script_blocks[0][1]
    stripped = "".join(
        line[2:] if len(line) > 1 and line[1] == " " else line[1:] for line in content.splitlines(keepends=True)
    )
    metadata = tomllib.loads(stripped)
    return ScriptMetadata(
        requires_python=metadata.get("requires-python"),
        dependencies=metadata.get("dependencies", []),
    )


__all__ = [
    "Pep723Mixin",
    "ScriptMetadata",
]
