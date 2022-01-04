from __future__ import annotations

import pytest
from pytest_mock import MockerFixture

from tox.pytest import ToxProjectCreator
from tox.report import HandledError
from tox.run import run


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


def test_custom_work_dir(tox_project: ToxProjectCreator) -> None:
    project = tox_project({})
    outcome = project.run("c", "--workdir", str(project.path.parent))
    assert outcome.state.conf.options.work_dir == project.path.parent
