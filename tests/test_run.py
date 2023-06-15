from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tox.report import HandledError
from tox.run import run

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize("exception", [HandledError, KeyboardInterrupt])
def test_exit_code_minus_2_on_expected_exit(exception: Exception, mocker: MockerFixture) -> None:
    mocker.patch("tox.run.main", side_effect=exception)
    with pytest.raises(SystemExit) as system_exit:
        run()
    assert system_exit.value.code == -2


def test_re_raises_on_unexpected_exit(mocker: MockerFixture) -> None:
    mocker.patch("tox.run.main", side_effect=ValueError)
    with pytest.raises(ValueError, match=""):  # noqa: PT011
        run()


def test_custom_work_dir(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    project = tox_project({})

    expected_tox_root = project.path
    expected_work_dir = tmp_path

    outcome = project.run("c", "--workdir", str(expected_work_dir))
    outcome.assert_success()

    assert outcome.state.conf.options.work_dir == expected_work_dir, "should parse the --workdir argument"

    assert outcome.state.conf.core["work_dir"], f"should set work_dir to {expected_work_dir}"

    assert outcome.state.conf.core["tox_root"] == expected_tox_root, "should not update the value of tox_root"
    assert outcome.state.conf.core["work_dir"] != (
        expected_tox_root / ".tox"
    ), "should explicitly demonstrate that tox_root and work_dir are decoupled"

    # should update config values that depend on work_dir
    assert outcome.state.conf.core["temp_dir"] == expected_work_dir / ".tmp"

    env_conf = outcome.state.conf.get_env("py")

    assert env_conf["env_dir"] == expected_work_dir / "py"
    assert env_conf["env_log_dir"] == expected_work_dir / "py" / "log"
    assert env_conf["env_tmp_dir"] == expected_work_dir / "py" / "tmp"


def test_custom_root_dir(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    project = tox_project({})

    expected_tox_root = tmp_path
    expected_work_dir = expected_tox_root / ".tox"

    outcome = project.run("c", "--root", str(expected_tox_root))
    outcome.assert_success()

    assert outcome.state.conf.options.root_dir == expected_tox_root, "should parse the --root argument"

    assert outcome.state.conf.core["tox_root"] == expected_tox_root, f"should set tox_root to {expected_tox_root}"

    # values that depend on tox_root should also be updated

    assert outcome.state.conf.core["work_dir"] == expected_work_dir
    assert outcome.state.conf.core["temp_dir"] == expected_work_dir / ".tmp"

    env_conf = outcome.state.conf.get_env("py")

    assert env_conf["env_dir"] == expected_work_dir / "py"
    assert env_conf["env_log_dir"] == expected_work_dir / "py" / "log"
    assert env_conf["env_tmp_dir"] == expected_work_dir / "py" / "tmp"


def test_custom_root_dir_and_work_dir(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    project = tox_project({})

    expected_tox_root = tmp_path / "tox_root"
    expected_work_dir = tmp_path / "work_dir"

    outcome = project.run("c", "--root", str(expected_tox_root), "--workdir", str(expected_work_dir))
    outcome.assert_success()

    assert outcome.state.conf.core["tox_root"] == expected_tox_root, f"should set tox_root to {expected_tox_root}"
    assert outcome.state.conf.core["work_dir"] == expected_work_dir, f"should set work_dir to {expected_work_dir}"

    # values that depend on work_dir should also be updated

    assert outcome.state.conf.core["temp_dir"] == expected_work_dir / ".tmp"

    env_conf = outcome.state.conf.get_env("py")

    assert env_conf["env_dir"] == expected_work_dir / "py"
    assert env_conf["env_log_dir"] == expected_work_dir / "py" / "log"
    assert env_conf["env_tmp_dir"] == expected_work_dir / "py" / "tmp"
