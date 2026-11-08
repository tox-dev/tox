from __future__ import annotations

from pathlib import Path
from typing import Any

from docutils.core import publish_string
from docutils.writers import get_writer_class
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(  # override signature
        self,
        version: str,  # ruff:ignore[unused-method-argument]  # override signature
        build_data: dict[str, Any],  # ruff:ignore[unused-method-argument]  # override signature  # simplint: ignore[SMP602]  # hatchling passes build data of any shape
    ) -> None:
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
                    writer=get_writer_class("manpage")(),
                    settings_overrides={"report_level": 5},
                )
            )
