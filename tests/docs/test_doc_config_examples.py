from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "filename" in metafunc.fixturenames:
        params = []
        for rel_file, line_no, lang, content in _extract_config_blocks():
            if not _is_tox_config(lang, content):
                continue
            filename, classified_content = _classify(lang, content)
            env_names = _find_env_names(filename, classified_content)
            commands = [("l",)] if env_names == ["__env_base__"] else [("c", "-e", env) for env in env_names]
            marks: list[pytest.MarkDecorator] = []
            if skip_reason := _should_skip(classified_content):
                marks.append(pytest.mark.skip(reason=skip_reason))
            params.append(pytest.param(filename, classified_content, commands, id=f"{rel_file}:{line_no}", marks=marks))
        metafunc.parametrize(("filename", "content", "commands"), params)


def _extract_config_blocks() -> list[tuple[str, int, str, str]]:
    results: list[tuple[str, int, str, str]] = []
    docs_dir = Path(__file__).parents[2] / "docs"
    for rst_path in sorted(docs_dir.rglob("*.rst")):
        lines = rst_path.read_text(encoding="utf-8").splitlines()
        idx = 0
        while idx < len(lines):
            if match := _CODE_BLOCK_RE.match(lines[idx]):
                directive_indent = len(match.group("indent")) + len(match.group("space")) + 2
                lang = match.group("lang")
                line_no = idx + 1
                content_lines, idx = _read_block(lines, idx + 1, directive_indent)
                if content_lines:
                    results.append((
                        str(rst_path.relative_to(docs_dir.parent)),
                        line_no,
                        lang,
                        textwrap.dedent("\n".join(content_lines)),
                    ))
            else:
                idx += 1
    return results


def _read_block(lines: list[str], idx: int, directive_indent: int) -> tuple[list[str], int]:
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    content_lines: list[str] = []
    while idx < len(lines):
        line = lines[idx]
        if not line.strip():
            content_lines.append("")
            idx += 1
            continue
        if (len(line) - len(line.lstrip())) > directive_indent:
            content_lines.append(line)
            idx += 1
        else:
            break
    while content_lines and not content_lines[-1].strip():
        content_lines.pop()
    return content_lines, idx


def _is_tox_config(lang: str, content: str) -> bool:
    if lang == "ini":
        return bool(
            _IS_TOX_CONFIG_PATTERN.search(content)
            or _IS_TOX_CONFIG_PATTERN_2.search(content)
            or _IS_TOX_CONFIG_PATTERN_3.search(content)
            or _IS_TOX_CONFIG_PATTERN_4.search(content)
        )
    first_section = _FIRST_SECTION_PATTERN.search(content)
    if first_section and first_section.group("section").split(".")[0].strip('"').strip("'") in {
        "build-system",
        "project",
        "project.entry-points.tox",
        "project.optional-dependencies",
    }:
        return False
    return bool(
        "legacy_tox_ini" in content
        or _IS_TOX_CONFIG_PATTERN_5.search(content)
        or _IS_TOX_CONFIG_PATTERN_6.search(content)
        or _IS_TOX_CONFIG_PATTERN_7.search(content)
        or _IS_TOX_CONFIG_PATTERN_8.search(content)
        or (_IS_TOX_CONFIG_PATTERN_9.search(content) and not first_section)
    )


def _classify(lang: str, content: str) -> tuple[str, str]:
    content = _replace_python_versions(content)
    if lang == "ini":
        filename, ini_content = _classify_ini(content)
        return filename, _inject_skip_missing_interpreters_ini(ini_content)
    if "legacy_tox_ini" in content:
        if not _CLASSIFY_PATTERN.search(content):
            content = f"[tool.tox]\n{content}"
        return "pyproject.toml", _inject_skip_missing_interpreters_toml(content, r"(\[tool\.tox\]\n)")
    if _CLASSIFY_PATTERN_2.search(content):
        return "pyproject.toml", _inject_skip_missing_interpreters_toml(content, r"(\[tool\.tox\]\n)")
    if _CLASSIFY_PATTERN_3.search(content):
        wrapped = _wrap_tox_toml_in_pyproject(content)
        return "pyproject.toml", _inject_skip_missing_interpreters_toml(wrapped, r"(\[tool\.tox\]\n)")
    return "tox.toml", _inject_skip_missing_interpreters_toml(content, r"^")


def _replace_python_versions(content: str) -> str:
    current_major = sys.version_info.major
    current_minor = sys.version_info.minor
    current_version = f"{current_major}.{current_minor}"
    current_py = f"py{current_major}{current_minor}"

    content = _CONTENT_PATTERN.sub(f"python{current_version}", content)
    content = _REPLACE_PYTHON_VERSIONS_PATTERN.sub(current_py, content)
    content = _REPLACE_PYTHON_VERSIONS_PATTERN_2.sub(f"cpython{current_version}", content)
    return _REPLACE_PYTHON_VERSIONS_PATTERN_3.sub(current_version, content)


def _classify_ini(content: str) -> tuple[str, str]:  # simplint: ignore[single-caller-helper]  # file kind
    if _CLASSIFY_INI_PATTERN.search(content):
        return "setup.cfg", content
    return (
        ("tox.ini", content)
        if (
            _CLASSIFY_INI_PATTERN_2.search(content)
            or _CLASSIFY_INI_PATTERN_3.search(content)
            or _CLASSIFY_INI_PATTERN_4.search(content)
            or _CLASSIFY_INI_PATTERN_5.search(content)
        )
        else ("tox.ini", f"[testenv]\n{content}")
    )


def _inject_skip_missing_interpreters_ini(content: str) -> str:
    if r"skip_missing_interpreters" in content:
        return content
    if not _INJECT_SKIP_MISSING_INTERPRETERS_INI_PATTERN.search(content):
        return f"[tox]\nskip_missing_interpreters = true\n{content}"
    return _INJECT_SKIP_MISSING_INTERPRETERS_INI_PATTERN_2.sub(r"\1skip_missing_interpreters = true\n", content)


def _inject_skip_missing_interpreters_toml(content: str, section_pattern: str) -> str:
    if r"skip_missing_interpreters" in content:
        return content
    if section_pattern == r"^":
        return f"skip_missing_interpreters = true\n{content}"
    return re.sub(section_pattern, r"\1skip_missing_interpreters = true\n", content)


def _wrap_tox_toml_in_pyproject(content: str) -> str:
    tox_lines: list[str] = []
    other_lines: list[str] = []
    in_tox = False
    in_other = False
    for line in content.splitlines():
        if section_match := _WRAP_TOX_TOML_IN_PYPROJECT_PATTERN.match(line):
            section = section_match.group("section")
            if section.startswith(("env", "env_run_base", "env_pkg_base", "env_base")):
                in_tox, in_other = True, False
                tox_lines.append(f"[tool.tox.{section}]")
                continue
            if section == "dependency-groups":
                in_tox, in_other = False, True
                other_lines.append(line)
                continue
            in_tox, in_other = True, False
            tox_lines.append(f"[tool.tox.{section}]")
            continue
        if in_tox:
            tox_lines.append(line)
        elif in_other:
            other_lines.append(line)
        elif line.strip() and not line.startswith("#"):
            tox_lines.append(line)
        else:
            other_lines.append(line)
    result = "[tool.tox]\n"
    if tox_lines:
        result += "\n".join([*tox_lines, ""])
    if other_lines:
        result += "\n".join(["", *other_lines, ""])
    return result


def _find_env_names(filename: str, content: str) -> list[str]:
    envs: list[str] = []
    if filename in {"tox.toml", "pyproject.toml"}:
        if _FIND_ENV_NAMES_PATTERN.search(content):
            return ["__env_base__"]
        for match in _MATCH_PATTERN.finditer(content):
            if (name := match.group("name").strip('"').strip("'")) not in envs:
                envs.append(name)
    elif filename in {"tox.ini", "setup.cfg"}:
        for match in _FIND_ENV_NAMES_PATTERN_2.finditer(content):
            raw = match.group("name")
            if "{" not in raw and raw not in envs:
                envs.append(raw)
    return envs or ["py"]


def _should_skip(content: str) -> str | None:
    if _SHOULD_SKIP_PATTERN.search(content):
        return "triggers auto-provisioning"
    if _SHOULD_SKIP_PATTERN_2.search(content):
        return "references architecture-specific Python"
    if _SHOULD_SKIP_PATTERN_3.search(content):
        return "requires specific virtualenv version"
    if _SHOULD_SKIP_PATTERN_4.search(content):
        return "tox output format, not input config"
    return None


_CODE_BLOCK_RE: Final[re.Pattern[str]] = re.compile(
    r"""
        ^(?P<indent>\s*)        # leading whitespace
        \.\.(?P<space>\s+)      # RST directive marker
        code-block::\s+         # code-block directive
        (?P<lang>toml|ini)      # language
        \s*$
        """,
    re.VERBOSE,
)


_IS_TOX_CONFIG_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\[tox(?::tox)?\]", re.MULTILINE)

_IS_TOX_CONFIG_PATTERN_2: Final[re.Pattern[str]] = re.compile(r"^\[testenv", re.MULTILINE)

_IS_TOX_CONFIG_PATTERN_3: Final[re.Pattern[str]] = re.compile(r"^\[pkgenv", re.MULTILINE)

_IS_TOX_CONFIG_PATTERN_4: Final[re.Pattern[str]] = re.compile(r"^\[base\]", re.MULTILINE)

_FIRST_SECTION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\[(?P<section>[^\]]+)\]", re.MULTILINE)

_IS_TOX_CONFIG_PATTERN_5: Final[re.Pattern[str]] = re.compile(
    r"""
            ^ \[ tool\.tox      # a tox table in a pyproject file
            """,
    re.MULTILINE | re.VERBOSE,
)

_IS_TOX_CONFIG_PATTERN_6: Final[re.Pattern[str]] = re.compile(
    r"""
            ^ \[                                  # the opening bracket of a table header
            (env|env_run_base|env_pkg_base|env_base)  # the environment table names
            \b                                    # the end of the name
            """,
    re.MULTILINE | re.VERBOSE,
)

_IS_TOX_CONFIG_PATTERN_7: Final[re.Pattern[str]] = re.compile(r"^env_list\s*=", re.MULTILINE)

_IS_TOX_CONFIG_PATTERN_8: Final[re.Pattern[str]] = re.compile(r"^(requires|no_package)\s*=", re.MULTILINE)

_IS_TOX_CONFIG_PATTERN_9: Final[re.Pattern[str]] = re.compile(r"^\w+\s*=", re.MULTILINE)


_CLASSIFY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\[tool\.tox\]", re.MULTILINE)

_CLASSIFY_PATTERN_2: Final[re.Pattern[str]] = re.compile(r"^\[tool\.tox", re.MULTILINE)

_CLASSIFY_PATTERN_3: Final[re.Pattern[str]] = re.compile(r"^\[dependency-groups\]", re.MULTILINE)


_CONTENT_PATTERN: Final[re.Pattern[str]] = re.compile(r"python3\.\d+")

_REPLACE_PYTHON_VERSIONS_PATTERN: Final[re.Pattern[str]] = re.compile(r"py\d{2,3}")

_REPLACE_PYTHON_VERSIONS_PATTERN_2: Final[re.Pattern[str]] = re.compile(r"cpython3\.\d+")

_REPLACE_PYTHON_VERSIONS_PATTERN_3: Final[re.Pattern[str]] = re.compile(r"(?<=[\s\[\"',=\-])3\.\d+")


_CLASSIFY_INI_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\[tox:tox\]", re.MULTILINE)

_CLASSIFY_INI_PATTERN_2: Final[re.Pattern[str]] = re.compile(r"^\[tox\]", re.MULTILINE)

_CLASSIFY_INI_PATTERN_3: Final[re.Pattern[str]] = re.compile(r"^\[testenv", re.MULTILINE)

_CLASSIFY_INI_PATTERN_4: Final[re.Pattern[str]] = re.compile(r"^\[pkgenv", re.MULTILINE)

_CLASSIFY_INI_PATTERN_5: Final[re.Pattern[str]] = re.compile(r"^\[base\]", re.MULTILINE)


_INJECT_SKIP_MISSING_INTERPRETERS_INI_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\[tox(?::tox)?\]", re.MULTILINE)

_INJECT_SKIP_MISSING_INTERPRETERS_INI_PATTERN_2: Final[re.Pattern[str]] = re.compile(r"(\[tox(?::tox)?\]\n)")


_WRAP_TOX_TOML_IN_PYPROJECT_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\[(?P<section>[^\]]+)\]")


_FIND_ENV_NAMES_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
            \[                  # the opening bracket of a table header
            (?:tool\.tox\.)?    # the optional pyproject prefix
            env_base\.          # the base environment table
            """,
    re.VERBOSE,
)

_MATCH_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
            \[                       # the opening bracket of a table header
            (?:tool\.tox\.)?         # the optional pyproject prefix
            env\.                     # the environment table prefix
            (?P<name> [^\]]+ )        # the environment name
            \]                       # the closing bracket of the table header
            """,
    re.VERBOSE,
)

_FIND_ENV_NAMES_PATTERN_2: Final[re.Pattern[str]] = re.compile(r"\[testenv:(?P<name>[^\]]+)\]")


_SHOULD_SKIP_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"""
        requires\s*=\s*\[?[^\]]*   # requires key with optional opening bracket
        (?:tox-uv|virtualenv[<>=!])  # matches tox-uv or virtualenv with version constraint
        """,
    re.VERBOSE | re.MULTILINE,
)

_SHOULD_SKIP_PATTERN_2: Final[re.Pattern[str]] = re.compile(
    r"""
        base_python\s*=\s*\[?\s*"?  # base_python key (not default_base_python)
        cpython3\.\d+-\d+-(?:arm64|x86_64)  # architecture-specific
        """,
    re.VERBOSE | re.MULTILINE,
)

_SHOULD_SKIP_PATTERN_3: Final[re.Pattern[str]] = re.compile(r"""virtualenv_spec\s*=""", re.MULTILINE)

_SHOULD_SKIP_PATTERN_4: Final[re.Pattern[str]] = re.compile(
    r"""
        ^commands\s*=\s*\[  # commands key with list
        "[^["]              # flat string list, not nested
        """,
    re.VERBOSE | re.MULTILINE,
)


def test_doc_config_valid(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content: str,
    commands: list[tuple[str, ...]],
) -> None:
    for key, value in {
        "CI": "1",
        "TAG_NAME": "v1.0",
        "VERBOSE": "1",
        "DEBUG": "1",
        "DEPLOY": "1",
        "LOCAL": "1",
        "L": "1",
        "X": "1",
        "MODE": "dev",
    }.items():
        monkeypatch.setenv(key, value)
    project = tox_project({filename: content})
    for command in commands:
        outcome = project.run(*command)
        outcome.assert_success()
        assert "# Exception:" not in outcome.out, f"Exception in {command}:\n{outcome.out}"
