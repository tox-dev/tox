from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.pytest import ToxProject, ToxProjectCreator


@pytest.mark.parametrize(
    ("shell_env", "rc_file"),
    [
        pytest.param({"SHELL": "/usr/bin/fish"}, "~/.config/fish/config.fish", id="fish"),
        pytest.param({"SHELL": "/bin/bash"}, "~/.bashrc", id="bash"),
        pytest.param({"SHELL": "/bin/zsh"}, "~/.zshrc", id="zsh"),
        pytest.param({"SHELL": "/etc/profiles/per-user/bashir/bin/zsh"}, "~/.zshrc", id="zsh-shell-name-in-dir"),
        pytest.param({"SHELL": "/bin/sh"}, "~/.profile", id="sh"),
        pytest.param({"SHELL": "/bin/ksh"}, "~/.profile", id="ksh"),
        pytest.param({}, "~/.profile", id="unset"),
        pytest.param({"SHELL": "/bin/csh"}, "~/.cshrc", id="csh"),
        pytest.param({"SHELL": "/bin/tcsh"}, "~/.cshrc", id="tcsh"),
    ],
)
def test_man_rc_file(
    man_project: ToxProject, monkeypatch: pytest.MonkeyPatch, shell_env: dict[str, str], rc_file: str
) -> None:
    monkeypatch.setattr(os, "environ", {k: v for k, v in os.environ.items() if k != "SHELL"} | shell_env)

    assert f"To complete setup, add this to {rc_file}:" in man_project.run("man").out


def test_man_rc_file_tcshrc_when_present(man_project: ToxProject, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SHELL", "/bin/tcsh")
    (Path.home() / ".tcshrc").touch()

    assert "To complete setup, add this to ~/.tcshrc:" in man_project.run("man").out


@pytest.mark.parametrize(
    ("shell", "export_line", "reload"),
    [
        pytest.param(
            "/usr/bin/fish",
            'set -x MANPATH "$HOME/.local/share/man:$MANPATH"',
            "source ~/.config/fish/config.fish",
            id="fish",
        ),
        pytest.param(
            "/bin/tcsh", 'setenv MANPATH "$HOME/.local/share/man:`printenv MANPATH`"', "source ~/.cshrc", id="tcsh"
        ),
        pytest.param("/bin/dash", 'export MANPATH="$HOME/.local/share/man:$MANPATH"', ". ~/.profile", id="dash"),
    ],
)
def test_man_shell_commands(
    man_project: ToxProject, monkeypatch: pytest.MonkeyPatch, shell: str, export_line: str, reload: str
) -> None:
    monkeypatch.setenv("SHELL", shell)

    assert f"  {export_line}\n\nThen restart your shell or run:\n  {reload}\n" in man_project.run("man").out


@pytest.fixture
def man_project(
    tox_project: ToxProjectCreator, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> ToxProject:
    if sys.platform == "win32":
        pytest.skip("creating symlinks needs privileges on Windows")
    man_page: Final = tmp_path / "prefix" / "share" / "man" / "man1" / "tox.1"
    man_page.parent.mkdir(parents=True)
    man_page.touch()
    monkeypatch.setattr(sys, "prefix", str(tmp_path / "prefix"))
    (home := tmp_path / "home").mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("MANPATH", raising=False)
    mocker.patch(
        "tox.session.cmd.man.subprocess.run",
        autospec=True,
        return_value=subprocess.CompletedProcess(args=["man", "tox"], returncode=16),
    )
    return tox_project({"tox.toml": ""})
