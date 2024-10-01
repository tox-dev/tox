from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

    from tox.pytest import ToxProjectCreator


def test_config_in_toml_core(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": """
    env_list = [ "A", "B"]

    [env_run_base]
    description = "Do magical things"
    commands = [
        ["python", "--version"],
        ["python", "-c", "import sys; print(sys.executable)"]
    ]
    """
    })

    outcome = project.run("c", "--core")
    outcome.assert_success()
    assert "# Exception: " not in outcome.out, outcome.out
    assert "# !!! unused: " not in outcome.out, outcome.out


def test_config_in_toml_non_default(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": """
    [env.C]
    description = "Do magical things in C"
    commands = [
        ["python", "--version"]
    ]
    """
    })

    outcome = project.run("c", "-e", "C", "--core")
    outcome.assert_success()
    assert "# Exception: " not in outcome.out, outcome.out
    assert "# !!! unused: " not in outcome.out, outcome.out


def test_config_in_toml_extra(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": """
    [env_run_base]
    description = "Do magical things"
    commands = [
        ["python", "--version"]
    ]
    """
    })

    outcome = project.run("c", "-e", ".".join(str(i) for i in sys.version_info[0:2]))
    outcome.assert_success()
    assert "# Exception: " not in outcome.out, outcome.out
    assert "# !!! unused: " not in outcome.out, outcome.out


def test_config_in_toml_replace_default(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": '[env_run_base]\ndescription = "{missing:miss}"'})
    outcome = project.run("c", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\ndescription = miss\n", "")


def test_config_in_toml_replace_env_name_via_env(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.toml": '[env_run_base]\ndescription = "Magic in {env:MAGICAL:{env_name}}"'})
    outcome = project.run("c", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\ndescription = Magic in py\n", "")


def test_config_in_toml_replace_env_name_via_env_set(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAGICAL", "YEAH")
    project = tox_project({"tox.toml": '[env_run_base]\ndescription = "Magic in {env:MAGICAL:{env_name}}"'})
    outcome = project.run("c", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\ndescription = Magic in YEAH\n", "")


def test_config_in_toml_replace_from_env_section_absolute(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": """
        [env.A]
        description = "a"
        [env.B]
        description = "{[env.A]env_name}"
        """
    })
    outcome = project.run("c", "-e", "B", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:B]\ndescription = A\n", "")


def test_config_in_toml_replace_from_section_absolute(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": """
        [extra]
        ok = "o"
        [env.B]
        description = "{[extra]ok}"
        """
    })
    outcome = project.run("c", "-e", "B", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:B]\ndescription = o\n", "")
