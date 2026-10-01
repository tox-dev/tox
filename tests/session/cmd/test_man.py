from __future__ import annotations

import pytest

from tox.session.cmd.man import _print_manpath_instructions  # ruff:ignore[import-private-name]


@pytest.mark.parametrize(
    ("shell", "rc_file"),
    [
        pytest.param("/usr/bin/fish", "~/.config/fish/config.fish", id="fish"),
        pytest.param("/bin/bash", "~/.bashrc", id="bash"),
        pytest.param("/bin/zsh", "~/.zshrc", id="zsh"),
        pytest.param("/bin/sh", "~/.profile", id="sh"),
        pytest.param("/bin/ksh", "~/.profile", id="ksh"),
        pytest.param("", "~/.profile", id="unset"),
    ],
)
def test_manpath_instructions_rc_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], shell: str, rc_file: str
) -> None:
    monkeypatch.setenv("SHELL", shell)

    _print_manpath_instructions()

    assert f"To complete setup, add this to {rc_file}:" in capsys.readouterr().out
