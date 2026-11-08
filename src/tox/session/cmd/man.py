from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from tox.plugin import impl

if TYPE_CHECKING:
    from tox.config.cli.parser import ToxParser
    from tox.session.state import State


@impl
def tox_add_option(parser: ToxParser) -> None:
    """Add the ``man`` sub-command to the command line parser.

    :param parser: the parser to add the sub-command to

    """
    from tox.config.cli.parser import CORE  # ruff:ignore[import-outside-top-level]  # avoids an import cycle

    parser.add_command("man", [], "Set up tox man page for current shell", setup_man, inherit=frozenset({CORE}))


def setup_man(state: State) -> int:  # ruff:ignore[unused-function-argument]  # interface signature
    """Show where the tox man page is, and how to install it for the current shell.

    :param state: the state of the run

    :returns: the exit code

    """
    print("tox man page setup")  # ruff:ignore[print]  # terminal output
    print("=" * 50)  # ruff:ignore[print]  # terminal output
    print()  # ruff:ignore[print]  # terminal output

    man_in_wheel = Path(sys.prefix) / "share" / "man" / "man1" / "tox.1"
    print(f"Looking for man page at: {man_in_wheel}")  # ruff:ignore[print]  # terminal output
    print()  # ruff:ignore[print]  # terminal output

    if not man_in_wheel.exists():
        print("✗ Man page not found")  # ruff:ignore[print]  # terminal output
        print(  # ruff:ignore[print]  # terminal output
            "  The man page should be included in the wheel when tox is installed."
        )
        print(  # ruff:ignore[print]  # terminal output
            "  If you installed from source or in development mode, the man page"
        )
        print(  # ruff:ignore[print]  # terminal output
            "  may not be present. Try installing from PyPI or use 'tox --help'."
        )
        return 1

    print("✓ Man page found")  # ruff:ignore[print]  # terminal output
    print()  # ruff:ignore[print]  # terminal output

    if _check_man_accessible():
        print("✓ 'man tox' already works!")  # ruff:ignore[print]  # terminal output
        print("  No setup needed.")  # ruff:ignore[print]  # terminal output
        return 0

    if (exit_code := _create_symlink(man_in_wheel)) != 0:
        return exit_code

    print()  # ruff:ignore[print]  # terminal output

    if str(Path.home() / ".local" / "share" / "man") in os.environ.get("MANPATH", ""):
        print("✓ MANPATH already includes ~/.local/share/man")  # ruff:ignore[print]  # terminal output
        print("  Try running: man tox")  # ruff:ignore[print]  # terminal output
        return 0

    print("⚠ MANPATH does not include ~/.local/share/man")  # ruff:ignore[print]  # terminal output
    print()  # ruff:ignore[print]  # terminal output
    _print_manpath_instructions()

    return 0


def _check_man_accessible() -> bool:  # simplint: ignore[SMP505]  # separates the man lookup from the instructions
    try:
        result = subprocess.run(  # resolved via PATH
            ["man", "tox"],  # ruff:ignore[start-process-with-partial-path]  # resolved via PATH
            capture_output=True,
            text=True,
            timeout=2,
            check=False,  # resolved via PATH
        )
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
            print(  # ruff:ignore[print]  # terminal output
                f"✓ Symlink already exists: {user_man_file} → {man_in_wheel}"
            )
            return 0
        print(f"✗ File already exists: {user_man_file}")  # ruff:ignore[print]  # terminal output
        print("  Remove it manually if you want to replace it.")  # ruff:ignore[print]  # terminal output
        return 1

    user_man_file.symlink_to(man_in_wheel)
    print(f"✓ Created symlink: {user_man_file} → {man_in_wheel}")  # ruff:ignore[print]  # terminal output
    return 0


def _print_manpath_instructions() -> None:  # simplint: ignore[SMP505]  # per-shell text, read apart from setup
    # each export line keeps a trailing ":" when MANPATH is unset, so man still searches its default path
    if "fish" in (shell := PurePath(os.environ.get("SHELL", "")).name):
        rc_file = "~/.config/fish/config.fish"
        export_line = 'set -x MANPATH "$HOME/.local/share/man:$MANPATH"'
        reload = "source"
    elif "csh" in shell:
        # tcsh, which macOS also ships as /bin/csh, skips ~/.cshrc when ~/.tcshrc exists
        rc_file = "~/.tcshrc" if (Path.home() / ".tcshrc").exists() else "~/.cshrc"
        # csh aborts on an unset $MANPATH, while printenv expands to nothing
        export_line = 'setenv MANPATH "$HOME/.local/share/man:`printenv MANPATH`"'
        reload = "source"
    else:
        rc_file = "~/.bashrc" if "bash" in shell else "~/.zshrc" if "zsh" in shell else "~/.profile"
        export_line = 'export MANPATH="$HOME/.local/share/man:$MANPATH"'
        reload = "."  # dash has no source builtin
    sys.stdout.write(
        f"To complete setup, add this to {rc_file}:\n\n  {export_line}\n\n"
        f"Then restart your shell or run:\n  {reload} {rc_file}\n\nAfter that, you can use: man tox\n"
    )


__all__ = [
    "setup_man",
]
