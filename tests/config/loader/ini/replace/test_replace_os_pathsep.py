from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.config.loader.ini.replace.conftest import ReplaceOne


def test_replace_os_pathsep(replace_one: ReplaceOne) -> None:
    result = replace_one("{:}")
    assert result == os.pathsep
