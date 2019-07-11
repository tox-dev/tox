import pytest

from tox.config.cli.parse import get_options


def test_help_does_not_default_cmd(capsys):
    with pytest.raises(SystemExit):
        get_options("-h")
    out, err = capsys.readouterr()
    assert not err
    assert "--verbose" in out
    assert "command:" in out
