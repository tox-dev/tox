import pytest

from tox.config.parallel import ENV_VAR_KEY_PRIVATE as PARALLEL_ENV_VAR_KEY_PRIVATE


def test_parallel_default(newconfig):
    config = newconfig([], "")
    assert isinstance(config.option.parallel, int)
    assert config.option.parallel == 0
    assert config.option.parallel_live is False


def test_parallel_live_on(newconfig):
    config = newconfig(["-o"], "")
    assert config.option.parallel_live is True


def test_parallel_auto(newconfig):
    config = newconfig(["-p", "auto"], "")
    assert isinstance(config.option.parallel, int)
    assert config.option.parallel > 0


def test_parallel_all(newconfig):
    config = newconfig(["-p", "all"], "")
    assert config.option.parallel is None


def test_parallel_number(newconfig):
    config = newconfig(["-p", "2"], "")
    assert config.option.parallel == 2


def test_parallel_number_negative(newconfig, capsys):
    with pytest.raises(SystemExit):
        newconfig(["-p", "-1"], "")

    out, err = capsys.readouterr()
    assert not out
    assert "value must be positive" in err


def test_depends(newconfig):
    config = newconfig(
        """\
        [tox]
        [testenv:py]
        depends = py37, py36
        """,
    )
    assert config.envconfigs["py"].depends == ("py37", "py36")


def test_depends_multi_row_facotr(newconfig):
    config = newconfig(
        """\
        [tox]
        [testenv:py]
        depends = py37,
                  {py36}-{a,b}
        """,
    )
    assert config.envconfigs["py"].depends == ("py37", "py36-a", "py36-b")


def test_depends_factor(newconfig):
    config = newconfig(
        """\
        [tox]
        [testenv:py]
        depends = {py37, py36}-{cov,no}
        """,
    )
    assert config.envconfigs["py"].depends == ("py37-cov", "py37-no", "py36-cov", "py36-no")


def test_parallel_env_selection_with_ALL(newconfig, monkeypatch):
    # Regression test for #2167
    inisource = """
        [tox]
        envlist = py,lint
    """
    monkeypatch.setenv(PARALLEL_ENV_VAR_KEY_PRIVATE, "py")
    config = newconfig(["-eALL"], inisource)
    assert config.envlist == ["py"]
    monkeypatch.setenv(PARALLEL_ENV_VAR_KEY_PRIVATE, "lint")
    config = newconfig(["-eALL"], inisource)
    assert config.envlist == ["lint"]
