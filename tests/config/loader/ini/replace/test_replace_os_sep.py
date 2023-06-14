from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tests.config.loader.ini.replace.conftest import ReplaceOne
    from tox.pytest import MonkeyPatch


def test_replace_os_sep(replace_one: ReplaceOne) -> None:
    result = replace_one("{/}")
    assert result == os.sep


@pytest.mark.parametrize("sep", ["/", "\\"])
def test_replace_os_sep_before_curly(monkeypatch: MonkeyPatch, replace_one: ReplaceOne, sep: str) -> None:
    """Explicit test case for issue #2732 (windows only)."""
    monkeypatch.setattr(os, "sep", sep)
    monkeypatch.delenv("_", raising=False)
    result = replace_one("{/}{env:_:foo}")
    assert result == os.sep + "foo"


@pytest.mark.parametrize("sep", ["/", "\\"])
def test_replace_os_sep_sub_exp_regression(monkeypatch: MonkeyPatch, replace_one: ReplaceOne, sep: str) -> None:
    monkeypatch.setattr(os, "sep", sep)
    monkeypatch.delenv("_", raising=False)
    result = replace_one("{env:_:{posargs}{/}.{posargs}}", ["foo"])
    assert result == f"foo{os.sep}.foo"
