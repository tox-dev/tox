import sys


def test_replace_pos_args_empty_sys_argv(replace_one, monkeypatch):
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{posargs}") as result:
        monkeypatch.setattr(sys, "argv", [])
    assert result.val == ""


def test_replace_pos_args_extra_sys_argv(replace_one, monkeypatch):
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{posargs}") as result:
        monkeypatch.setattr(sys, "argv", [sys.executable, "magic"])
    assert result.val == ""


def test_replace_pos_args(replace_one, monkeypatch):
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one("{posargs}") as result:
        monkeypatch.setattr(sys, "argv", [sys.executable, "magic", "--", "ok", "what", " yes "])
    assert result.val == "ok what ' yes '"
