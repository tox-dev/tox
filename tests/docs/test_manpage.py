from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

from tox.config.cli.manpage import main

if sys.platform == "win32":
    pytest.skip("man command not available on Windows", allow_module_level=True)

_ROOT: Final[Path] = Path(__file__).parents[2]
_RST_PATH: Final[Path] = _ROOT / "docs" / "man" / "tox.1.rst"


def test_generated_manpage_has_cli_commands_and_options(tmp_path: Path) -> None:
    generated = tmp_path / "tox.1.rst"
    main(generated)
    content = generated.read_text(encoding="utf-8")
    assert "**run**" in content
    assert "**--help**" in content
    assert "ENVIRONMENT VARIABLES" in content


@pytest.fixture
def manpage_troff() -> bytes:
    from docutils.core import publish_string  # ruff:ignore[import-outside-top-level]  # deferred import
    from docutils.writers import get_writer_class  # ruff:ignore[import-outside-top-level]  # deferred import

    content = "\n".join(
        line for line in _RST_PATH.read_text(encoding="utf-8").splitlines() if line.strip() != ":orphan:"
    )
    return publish_string(content, writer=get_writer_class("manpage")(), settings_overrides={"report_level": 5})


_MANPAGE_RENDERED_PATTERN: Final[re.Pattern[str]] = re.compile(r".\x08")


@pytest.fixture
def manpage_rendered(manpage_troff: bytes, tmp_path: Path) -> str:
    man_file = tmp_path / "tox.1"
    man_file.write_bytes(manpage_troff)
    result = subprocess.run(
        ["man", str(man_file)],  # ruff:ignore[start-process-with-partial-path]  # resolved via PATH
        capture_output=True,
        text=True,
        env={"COLUMNS": "200", "LANG": "en_US.UTF-8", "PATH": "/usr/bin:/bin", "MANPAGER": "cat", "PAGER": "cat"},
        check=False,
    )
    return _MANPAGE_RENDERED_PATTERN.sub("", result.stdout)


_MATCH_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
        ^ \.TH [ ]                    # the title header macro
        " (?P<program> [^"]* ) "      # the program name
        [ ] " (?P<section> [^"]* ) "  # the manual section
        [ ] " (?P<date> [^"]* ) "     # the date
        [ ] " (?P<source> [^"]* ) "   # the source of the page
        [ ] " (?P<manual> [^"]* ) "   # the manual title
        """,
    re.MULTILINE | re.VERBOSE,
)


def test_manpage_has_title_header(manpage_troff: bytes) -> None:
    output = manpage_troff.decode()
    match = _MATCH_PATTERN.search(output)
    assert match is not None, f".TH header not found in:\n{output[:500]}"
    assert (match["program"], match["section"], match["manual"]) == ("tox", "1", "User Commands")


_TEST_MANPAGE_HAS_NAME_SECTION_PATTERN: Final[re.Pattern[str]] = re.compile(r"\.SH Name\n(?P<body>.+)")


def test_manpage_has_name_section(manpage_troff: bytes) -> None:
    match = _TEST_MANPAGE_HAS_NAME_SECTION_PATTERN.search(manpage_troff.decode())
    assert match is not None, "Name section not found"
    assert "tox" in match["body"]
    assert "virtualenv-based automation of test activities" in match["body"]


_SECTIONS_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\.SH (.+)$", re.MULTILINE)


def test_manpage_has_all_sections(manpage_troff: bytes) -> None:
    sections = _SECTIONS_PATTERN.findall(manpage_troff.decode())
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


@pytest.fixture(scope="module")
def tox_help() -> str:
    return subprocess.run([sys.executable, "-m", "tox", "--help"], capture_output=True, text=True, check=True).stdout


def test_manpage_documents_all_commands(tox_help: str) -> None:
    rst = _RST_PATH.read_text(encoding="utf-8")
    names = [line.split()[0] for line in tox_help.split("subcommands:", 1)[1].splitlines() if line.startswith("    ")]
    assert names
    for name in names:
        assert f"**{name}**" in rst, (
            f"command {name!r} missing from manpage, regenerate with: python tools/generate_manpage.py"
        )


def test_manpage_documents_all_options(tox_help: str) -> None:
    rst = _RST_PATH.read_text(encoding="utf-8")
    names = [
        name.rstrip(",")
        for line in tox_help.splitlines()
        if line.startswith("  -")
        for name in line.strip().split("  ", 1)[0].split()
        if name.startswith("--")
    ]
    assert names
    for name in names:
        assert f"**{name}**" in rst, (
            f"option {name!r} missing from manpage, regenerate with: python tools/generate_manpage.py"
        )
