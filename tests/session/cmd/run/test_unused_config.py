from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_unused_config_testenv_warns_at_verbose(tox_project: ToxProjectCreator) -> None:
    toml = '[env_run_base]\npackage = "skip"\ncommands = [["python", "-c", ""]]\nbogus_key = "yes"\n'
    outcome = tox_project({"tox.toml": toml}).run("r", "-v")
    outcome.assert_success()
    assert "[testenv:py] unused config key(s): bogus_key" in outcome.out


def test_unused_config_core_warns_at_verbose(tox_project: ToxProjectCreator) -> None:
    toml = 'not_a_real_key = "yes"\n[env_run_base]\npackage = "skip"\ncommands = [["python", "-c", ""]]\n'
    outcome = tox_project({"tox.toml": toml}).run("r", "-v")
    outcome.assert_success()
    assert "[tox] unused config key(s): not_a_real_key" in outcome.out


def test_unused_config_no_warning_at_default_verbosity(tox_project: ToxProjectCreator) -> None:
    toml = '[env_run_base]\npackage = "skip"\ncommands = [["python", "-c", ""]]\nbogus_key = "yes"\n'
    outcome = tox_project({"tox.toml": toml}).run("r")
    outcome.assert_success()
    assert "unused config key" not in outcome.out


def test_no_unused_config_warning_when_all_valid(tox_project: ToxProjectCreator) -> None:
    toml = '[env_run_base]\npackage = "skip"\ncommands = [["python", "-c", ""]]\n'
    outcome = tox_project({"tox.toml": toml}).run("r", "-v")
    outcome.assert_success()
    assert "unused config key" not in outcome.out
