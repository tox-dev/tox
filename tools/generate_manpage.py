"""Generate the static manpage RST from the CLI parser."""  # ruff:ignore[implicit-namespace-package]  # standalone script

from __future__ import annotations

from pathlib import Path

from tox.config.cli.manpage import main

if __name__ == "__main__":
    main(Path(__file__).parents[1] / "docs" / "man" / "tox.1.rst")
