from __future__ import annotations

from pathlib import Path
from typing import Any

from docutils.core import publish_string
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:  # noqa: ARG002
        if self.target_name == "wheel":
            root = Path(self.root)
            (output := root / "build" / "man").mkdir(parents=True, exist_ok=True)
            (output / "tox.1").write_bytes(
                publish_string(
                    "\n".join(
                        line
                        for line in (root / "docs" / "man" / "tox.1.rst").read_text(encoding="utf-8").splitlines()
                        if line.strip() != ":orphan:"
                    ),
                    writer="manpage",
                    settings_overrides={"report_level": 5},
                )
            )
