import pytest
from pytest_mock import MockerFixture

import tox.run
from tox.report import HandledError


@pytest.mark.parametrize("exception", [HandledError, KeyboardInterrupt])
def test_run_raises_SystemExit_with_negative_two_exit_code_when_main_throws_expected_exception(
    exception: Exception, mocker: MockerFixture
) -> None:
    mocker.patch.object(tox.run, "main", side_effect=exception)
    with pytest.raises(SystemExit) as system_exit:
        tox.run.run()
    assert system_exit.value.code == -2


def test_run_reraises_when_main_throws_unexpected_exception(mocker: MockerFixture) -> None:
    mocker.patch.object(tox.run, "main", side_effect=ValueError)
    with pytest.raises(ValueError):
        tox.run.run()
