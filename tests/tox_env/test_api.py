from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.tox_env.api import redact_value

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


def test_ensure_temp_dir_exists(tox_project: ToxProjectCreator) -> None:
    ini = "[testenv]\ncommands=python -c 'import os; os.path.exists(r\"{temp_dir}\")'"
    project = tox_project({"tox.ini": ini})
    result = project.run()
    result.assert_success()


def test_dont_cleanup_temp_dir(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    (tmp_path / "foo" / "bar").mkdir(parents=True)
    project = tox_project({"tox.ini": "[tox]\ntemp_dir=foo"})
    result = project.run()
    result.assert_success()
    assert (tmp_path / "foo" / "bar").exists()


def test_setenv_section_substitution(tox_project: ToxProjectCreator) -> None:
    ini = """[variables]
    var = VAR = val
    [testenv]
    setenv = {[variables]var}
    commands = python -c 'import os; os.environ["VAR"]'"""
    project = tox_project({"tox.ini": ini})
    result = project.run()
    result.assert_success()


@pytest.mark.parametrize(
    ("key", "do_redact"),
    [
        pytest.param("SOME_KEY", True, id="key"),
        pytest.param("API_FOO", True, id="api"),
        pytest.param("AUTH", True, id="auth"),
        pytest.param("CLIENT", True, id="client"),
        pytest.param("DB_PASSWORD", True, id="password"),
        pytest.param("FOO", False, id="foo"),
        pytest.param("GITHUB_TOKEN", True, id="token"),
        pytest.param("NORMAL_VAR", False, id="other"),
        pytest.param("S_PASSWD", True, id="passwd"),
        pytest.param("SECRET", True, id="secret"),
        pytest.param("SOME_ACCESS", True, id="access"),
        pytest.param("MY_CRED", True, id="cred"),
        pytest.param("MY_PRIVATE", True, id="private"),
        pytest.param("MY_PWD", True, id="pwd"),
    ],
)
def test_redact(key: str, do_redact: bool) -> None:
    """Ensures that redact_value works as expected."""
    result = redact_value(key, "foo")
    if do_redact:
        assert result == "***"
    else:
        assert result == "foo"
