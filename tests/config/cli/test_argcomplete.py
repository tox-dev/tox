from __future__ import annotations

from typing import TYPE_CHECKING

import argcomplete

from tox.config.cli.parse import get_options

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_argcomplete_autocomplete_called(mocker: MockerFixture) -> None:
    mock_autocomplete = mocker.patch.object(argcomplete, "autocomplete")
    get_options("r")
    mock_autocomplete.assert_called_once()


def test_argcomplete_missing_does_not_break(mocker: MockerFixture) -> None:
    mocker.patch.dict("sys.modules", {"argcomplete": None})
    result = get_options("r")
    assert result.parsed is not None
