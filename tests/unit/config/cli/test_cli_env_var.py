import pytest

from tox.config.cli.parse import get_options


def test_env_var_exhaustive_parallel_values(monkeypatch, core_handlers):
    monkeypatch.setenv("TOX_COMMAND", "run-parallel")
    monkeypatch.setenv("TOX_VERBOSE", "5")
    monkeypatch.setenv("TOX_QUIET", "1")
    monkeypatch.setenv("TOX_ENV_LIST", "py37,py36")
    monkeypatch.setenv("TOX_DEFAULT_RUNNER", "magic")
    monkeypatch.setenv("TOX_RECREATE", "yes")
    monkeypatch.setenv("TOX_NO_TEST", "yes")
    monkeypatch.setenv("TOX_PARALLEL", "3")
    monkeypatch.setenv("TOX_PARALLEL_LIVE", "no")

    parsed, unknown, handlers = get_options()
    assert vars(parsed) == {
        "verbose": 5,
        "quiet": 1,
        "command": "run-parallel",
        "env_list": ["py37", "py36"],
        "default_runner": "magic",
        "recreate": True,
        "no_test": True,
        "parallel": 3,
        "parallel_live": False,
    }
    assert parsed.verbosity == 4
    assert unknown == []
    assert handlers == core_handlers


def test_ini_help(monkeypatch, capsys):
    monkeypatch.setenv("TOX_VERBOSE", "5")
    monkeypatch.setenv("TOX_QUIET", "1")
    with pytest.raises(SystemExit) as context:
        get_options("-h")
    assert context.value.code == 0
    out, err = capsys.readouterr()
    assert not err
    assert "from env var TOX_VERBOSE" in out
    assert "from env var TOX_QUIET" in out


def test_bad_env_var(monkeypatch, capsys, caplog):
    monkeypatch.setenv("TOX_VERBOSE", "should-be-number")
    monkeypatch.setenv("TOX_QUIET", "1.00")
    parsed, _, __ = get_options()
    assert parsed.verbose == 2
    assert parsed.quiet == 0
    assert parsed.verbosity == 2
    assert caplog.messages == [
        "env var TOX_VERBOSE='should-be-number' cannot be transformed to <class 'int'> "
        "because ValueError(\"invalid literal for int() with base 10: 'should-be-number'\")",
        "env var TOX_QUIET='1.00' cannot be transformed to <class 'int'> "
        "because ValueError(\"invalid literal for int() with base 10: '1.00'\")",
    ]
