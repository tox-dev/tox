from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from tox.plugin import impl

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    from tox.config.cli.parser import CORE  # noqa: PLC0415

    parser.add_command("man", [], "Set up tox man page for current shell", setup_man, inherit=frozenset({CORE}))


def setup_man(state: State) -> int:  # noqa: ARG001
    print("tox man page setup")  # noqa: T201
    print("=" * 50)  # noqa: T201
    print()  # noqa: T201

    man_in_wheel = Path(sys.prefix) / "share" / "man" / "man1" / "tox.1"
    print(f"Looking for man page at: {man_in_wheel}")  # noqa: T201
    print()  # noqa: T201

    if not man_in_wheel.exists():
        print("✗ Man page not found")  # noqa: T201
        print("  The man page should be included in the wheel when tox is installed.")  # noqa: T201
        print("  If you installed from source or in development mode, the man page")  # noqa: T201
        print("  may not be present. Try installing from PyPI or use 'tox --help'.")  # noqa: T201
        return 1

    print("✓ Man page found")  # noqa: T201
    print()  # noqa: T201

    if _check_man_accessible():
        print("✓ 'man tox' already works!")  # noqa: T201
        print("  No setup needed.")  # noqa: T201
        return 0

    if (exit_code := _create_symlink(man_in_wheel)) != 0:
        return exit_code

    print()  # noqa: T201

    manpath = os.environ.get("MANPATH", "")
    user_man_base = str(Path.home() / ".local" / "share" / "man")

    if user_man_base in manpath:
        print("✓ MANPATH already includes ~/.local/share/man")  # noqa: T201
        print("  Try running: man tox")  # noqa: T201
        return 0

    print("⚠ MANPATH does not include ~/.local/share/man")  # noqa: T201
    print()  # noqa: T201
    _print_manpath_instructions()

    return 0


def _check_man_accessible() -> bool:
    try:
        result = subprocess.run(["man", "tox"], capture_output=True, text=True, timeout=2, check=False)  # noqa: S607
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    else:
        return result.returncode == 0


def _create_symlink(man_in_wheel: Path) -> int:
    user_man_dir = Path.home() / ".local" / "share" / "man" / "man1"
    user_man_file = user_man_dir / "tox.1"

    user_man_dir.mkdir(parents=True, exist_ok=True)

    if user_man_file.exists() or user_man_file.is_symlink():
        if user_man_file.is_symlink() and user_man_file.resolve() == man_in_wheel:
            print(f"✓ Symlink already exists: {user_man_file} → {man_in_wheel}")  # noqa: T201
            return 0
        print(f"✗ File already exists: {user_man_file}")  # noqa: T201
        print("  Remove it manually if you want to replace it.")  # noqa: T201
        return 1

    user_man_file.symlink_to(man_in_wheel)
    print(f"✓ Created symlink: {user_man_file} → {man_in_wheel}")  # noqa: T201
    return 0


def _print_manpath_instructions() -> None:
    shell = os.environ.get("SHELL", "")
    is_fish = "fish" in shell

    rc_file = {
        True: "~/.config/fish/config.fish",
        "bash" in shell: "~/.bashrc",
        "zsh" in shell: "~/.zshrc",
    }.get(is_fish or any(s in shell for s in ("bash", "zsh")), "~/.profile")

    print(f"To complete setup, add this to {rc_file}:")  # noqa: T201
    print()  # noqa: T201

    export_line = (
        'set -x MANPATH "$HOME/.local/share/man" $MANPATH'
        if is_fish
        else 'export MANPATH="$HOME/.local/share/man:$MANPATH"'
    )
    print(f"  {export_line}")  # noqa: T201
    print()  # noqa: T201
    print("Then restart your shell or run:")  # noqa: T201
    print(f"  source {rc_file}")  # noqa: T201
    print()  # noqa: T201
    print("After that, you can use: man tox")  # noqa: T201
