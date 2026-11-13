from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator

_DOCS_DIR: Final[Path] = Path(__file__).parents[2] / "docs"
_PYTHON_BLOCK: Final[re.Pattern[str]] = re.compile(
    r"""
    ^ \.\.[ ]code-block::[ ]python \n  # the python code block directive
    \n                                       # a blank line before the body
    (?P<body> (?: (?: [ ]{4} .* )? \n )+ )   # the indented body lines, blank lines included
    """,
    re.MULTILINE | re.VERBOSE,
)


_EXPECTED_PATTERN: Final[re.Pattern[str]] = re.compile(r'return "(?P<info>[^"]+)"')


def _version_info_examples() -> list[tuple[str, str]]:
    examples = []
    for rel_path in ("plugin/getting_started.rst", "plugin/howto.rst"):
        for match in _PYTHON_BLOCK.finditer((_DOCS_DIR / rel_path).read_text(encoding="utf-8")):
            code = textwrap.dedent(match.group("body"))
            if "def tox_append_version_info" in code:
                expected = _EXPECTED_PATTERN.search(code)
                assert expected is not None
                examples.append((code, expected.group("info")))
    return examples


@pytest.mark.plugin_test
@pytest.mark.parametrize(
    ("code", "expected"),
    [
        pytest.param(*case, id=name)
        for case, name in zip(_version_info_examples(), ("getting_started", "howto"), strict=True)
    ],
)
def test_doc_append_version_info_example(tox_project: ToxProjectCreator, code: str, expected: str) -> None:
    outcome = tox_project({"tox.ini": "", "toxfile.py": code}).run("--version")
    outcome.assert_success()
    assert f"toxfile.py {expected}" in outcome.out
