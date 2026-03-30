from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

if sys.platform == "win32":
    pytest.skip("man command not available on Windows", allow_module_level=True)

ROOT = Path(__file__).parents[2]
RST_PATH = ROOT / "docs" / "man" / "tox.1.rst"


@pytest.fixture
def manpage_troff() -> bytes:
    from docutils.core import publish_string  # noqa: PLC0415

    content = "\n".join(
        line for line in RST_PATH.read_text(encoding="utf-8").splitlines() if line.strip() != ":orphan:"
    )
    return publish_string(content, writer="manpage", settings_overrides={"report_level": 5})


@pytest.fixture
def manpage_rendered(manpage_troff: bytes, tmp_path: Path) -> str:
    man_file = tmp_path / "tox.1"
    man_file.write_bytes(manpage_troff)
    result = subprocess.run(
        ["man", str(man_file)],  # noqa: S607
        capture_output=True,
        text=True,
        env={"COLUMNS": "200", "LANG": "en_US.UTF-8", "PATH": "/usr/bin:/bin", "MANPAGER": "cat", "PAGER": "cat"},
        check=False,
    )
    return re.sub(r".\x08", "", result.stdout)


def test_manpage_has_title_header(manpage_troff: bytes) -> None:
    output = manpage_troff.decode()
    match = re.search(r'^\.TH "([^"]*)" "([^"]*)" "([^"]*)" "([^"]*)" "([^"]*)"', output, re.MULTILINE)
    assert match is not None, f".TH header not found in:\n{output[:500]}"
    assert match.group(1) == "tox"
    assert match.group(2) == "1"
    assert match.group(5) == "User Commands"


def test_manpage_has_name_section(manpage_troff: bytes) -> None:
    output = manpage_troff.decode()
    match = re.search(r"\.SH Name\n(.+)", output)
    assert match is not None, "Name section not found"
    assert "tox" in match.group(1)
    assert "virtualenv-based automation of test activities" in match.group(1)


def test_manpage_has_all_sections(manpage_troff: bytes) -> None:
    output = manpage_troff.decode()
    sections = re.findall(r"^\.SH (.+)$", output, re.MULTILINE)
    expected = [
        "Name",
        "SYNOPSIS",
        "DESCRIPTION",
        "COMMANDS",
        "OPTIONS",
        "FILES",
        "ENVIRONMENT VARIABLES",
        "SEE ALSO",
        "AUTHOR",
    ]
    assert sections == expected


def test_manpage_renders_sections(manpage_rendered: str) -> None:
    assert "tox" in manpage_rendered
    for section in ("SYNOPSIS", "DESCRIPTION", "COMMANDS", "OPTIONS", "FILES", "SEE ALSO", "AUTHOR"):
        assert section in manpage_rendered, f"section {section!r} missing from rendered man output"


def test_manpage_name_not_empty(manpage_rendered: str) -> None:
    lines = manpage_rendered.splitlines()
    name_idx = next((i for i, line in enumerate(lines) if "Name" in line or "NAME" in line), None)
    assert name_idx is not None, "NAME section not found in rendered output"
    name_line = lines[name_idx + 1].strip()
    assert "tox" in name_line
    assert "virtualenv-based automation of test activities" in name_line


def test_manpage_header_shows_tox(manpage_rendered: str) -> None:
    first_line = manpage_rendered.splitlines()[0]
    assert "tox" in first_line.lower()


def test_manpage_documents_all_commands() -> None:
    from argparse import _SubParsersAction  # noqa: PLC0415, PLC2701

    from tox.config.cli.parse import _get_parser_doc  # noqa: PLC0415, PLC2701

    parser = _get_parser_doc()
    rst = RST_PATH.read_text(encoding="utf-8")
    assert parser._subparsers is not None  # noqa: SLF001
    for action in parser._subparsers._actions:  # noqa: SLF001
        if isinstance(action, _SubParsersAction):
            for choice_action in action._choices_actions:  # noqa: SLF001
                assert choice_action.dest in rst, (
                    f"command {choice_action.dest!r} missing from manpage, regenerate with: "
                    f"python tools/generate_manpage.py"
                )


def test_manpage_documents_all_options() -> None:
    from argparse import SUPPRESS, _SubParsersAction  # noqa: PLC0415, PLC2701

    from tox.config.cli.parse import _get_parser_doc  # noqa: PLC0415, PLC2701

    parser = _get_parser_doc()
    rst = RST_PATH.read_text(encoding="utf-8")
    seen: set[int] = set()
    for action in parser._actions:  # noqa: SLF001
        if id(action) in seen or action.help == SUPPRESS or isinstance(action, _SubParsersAction):
            continue
        seen.add(id(action))
        if not action.option_strings:
            continue
        long_opt = next((o for o in action.option_strings if o.startswith("--")), action.option_strings[0])
        assert long_opt in rst, (
            f"option {long_opt!r} missing from manpage, regenerate with: python tools/generate_manpage.py"
        )
