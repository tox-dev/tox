from __future__ import annotations

import os

from tests.config.loader.ini.replace.conftest import ReplaceOne


def test_replace_os_sep(replace_one: ReplaceOne) -> None:
    result = replace_one("{/}")
    assert result == os.sep
