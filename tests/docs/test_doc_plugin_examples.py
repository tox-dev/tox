from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator

DOCS_DIR = Path(__file__).parents[2] / "docs"
PYTHON_BLOCK = re.compile(r"^\.\. code-block:: python\n\n(?P<body>(?:(?: {4}.*)?\n)+)", re.MULTILINE)


def _version_info_examples() -> list[tuple[str, str]]:
    examples = []
    for rel_path in ("plugin/getting_started.rst", "plugin/howto.rst"):
        for match in PYTHON_BLOCK.finditer((DOCS_DIR / rel_path).read_text(encoding="utf-8")):
            code = textwrap.dedent(match.group("body"))
            if "def tox_append_version_info" in code:
                expected = re.search(r'return "(?P<info>[^"]+)"', code)
                assert expected is not None
                examples.append((code, expected.group("info")))
    return examples


@pytest.mark.plugin_test
@pytest.mark.parametrize(("code", "expected"), _version_info_examples(), ids=["getting_started", "howto"])
def test_doc_append_version_info_example(tox_project: ToxProjectCreator, code: str, expected: str) -> None:
    project = tox_project({"tox.ini": "", "toxfile.py": code})
    outcome = project.run("--version")
    outcome.assert_success()
    assert f"toxfile.py {expected}" in outcome.out
