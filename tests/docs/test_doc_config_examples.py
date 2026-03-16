from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

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
            marks: list[pytest.MarkDecorator] = []
            if skip_reason := _should_skip(classified_content):
                marks.append(pytest.mark.skip(reason=skip_reason))
            params.append(
                pytest.param(filename, classified_content, env_names, id=f"{rel_file}:{line_no}", marks=marks)
            )
        metafunc.parametrize(("filename", "content", "env_names"), params)


def test_doc_config_valid(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content: str,
    env_names: list[str],
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
    if env_names == ["__env_base__"]:
        outcome = project.run("l")
        outcome.assert_success()
        return
    for env in env_names:
        outcome = project.run("c", "-e", env)
        outcome.assert_success()
        assert "# Exception:" not in outcome.out, f"Exception in {env}:\n{outcome.out}"


def _extract_config_blocks() -> list[tuple[str, int, str, str]]:
    results: list[tuple[str, int, str, str]] = []
    docs_dir = Path(__file__).parents[2] / "docs"
    code_block_re = re.compile(
        r"""
        ^(?P<indent>\s*)        # leading whitespace
        \.\.(?P<space>\s+)      # RST directive marker
        code-block::\s+         # code-block directive
        (?P<lang>toml|ini)      # language
        \s*$
        """,
        re.VERBOSE,
    )
    for rst_path in sorted(docs_dir.rglob("*.rst")):
        lines = rst_path.read_text(encoding="utf-8").splitlines()
        idx = 0
        while idx < len(lines):
            if match := code_block_re.match(lines[idx]):
                directive_indent = len(match.group("indent")) + len(match.group("space")) + 2
                lang = match.group("lang")
                line_no = idx + 1
                idx += 1
                while idx < len(lines) and not lines[idx].strip():
                    idx += 1
                content_lines: list[str] = []
                while idx < len(lines):
                    line = lines[idx]
                    if not line.strip():
                        content_lines.append("")
                        idx += 1
                        continue
                    current_indent = len(line) - len(line.lstrip())
                    if current_indent > directive_indent:
                        content_lines.append(line)
                        idx += 1
                    else:
                        break
                while content_lines and not content_lines[-1].strip():
                    content_lines.pop()
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


def _is_tox_config(lang: str, content: str) -> bool:
    if lang == "ini":
        return bool(
            re.search(r"^\[tox(?::tox)?\]", content, re.MULTILINE)
            or re.search(r"^\[testenv", content, re.MULTILINE)
            or re.search(r"^\[pkgenv", content, re.MULTILINE)
            or re.search(r"^\[base\]", content, re.MULTILINE)
        )
    first_section = re.search(r"^\[(?P<section>[^\]]+)\]", content, re.MULTILINE)
    if first_section and first_section.group("section").split(".")[0].strip('"').strip("'") in {
        "build-system",
        "project",
        "project.entry-points.tox",
        "project.optional-dependencies",
    }:
        return False
    return bool(
        "legacy_tox_ini" in content
        or re.search(r"^\[tool\.tox", content, re.MULTILINE)
        or re.search(r"^\[(env|env_run_base|env_pkg_base|env_base)\b", content, re.MULTILINE)
        or re.search(r"^env_list\s*=", content, re.MULTILINE)
        or re.search(r"^(requires|no_package)\s*=", content, re.MULTILINE)
        or (re.search(r"^\w+\s*=", content, re.MULTILINE) and not first_section)
    )


def _replace_python_versions(content: str) -> str:
    current_major = sys.version_info.major
    current_minor = sys.version_info.minor
    current_version = f"{current_major}.{current_minor}"
    current_py = f"py{current_major}{current_minor}"

    content = re.sub(r"python3\.\d+", f"python{current_version}", content)
    content = re.sub(r"py\d{2,3}", current_py, content)
    content = re.sub(r"cpython3\.\d+", f"cpython{current_version}", content)
    return re.sub(r"(?<=[\s\[\"',=])3\.\d+", current_version, content)


def _classify(lang: str, content: str) -> tuple[str, str]:
    content = _replace_python_versions(content)
    if lang == "ini":
        filename, ini_content = _classify_ini(content)
        return filename, _inject_skip_missing_interpreters_ini(ini_content)
    if "legacy_tox_ini" in content:
        if not re.search(r"^\[tool\.tox\]", content, re.MULTILINE):
            content = f"[tool.tox]\n{content}"
        return "pyproject.toml", _inject_skip_missing_interpreters_toml(content, r"(\[tool\.tox\]\n)")
    if re.search(r"^\[tool\.tox", content, re.MULTILINE):
        return "pyproject.toml", _inject_skip_missing_interpreters_toml(content, r"(\[tool\.tox\]\n)")
    if re.search(r"^\[dependency-groups\]", content, re.MULTILINE):
        wrapped = _wrap_tox_toml_in_pyproject(content)
        return "pyproject.toml", _inject_skip_missing_interpreters_toml(wrapped, r"(\[tool\.tox\]\n)")
    return "tox.toml", _inject_skip_missing_interpreters_toml(content, r"^")


def _inject_skip_missing_interpreters_ini(content: str) -> str:
    if r"skip_missing_interpreters" in content:
        return content
    if not re.search(r"^\[tox(?::tox)?\]", content, re.MULTILINE):
        return "[tox]\nskip_missing_interpreters = true\n" + content
    return re.sub(r"(\[tox(?::tox)?\]\n)", r"\1skip_missing_interpreters = true\n", content)


def _inject_skip_missing_interpreters_toml(content: str, section_pattern: str) -> str:
    if r"skip_missing_interpreters" in content:
        return content
    if section_pattern == r"^":
        return "skip_missing_interpreters = true\n" + content
    return re.sub(section_pattern, r"\1skip_missing_interpreters = true\n", content)


def _classify_ini(content: str) -> tuple[str, str]:
    if re.search(r"^\[tox:tox\]", content, re.MULTILINE):
        return "setup.cfg", content
    return (
        ("tox.ini", content)
        if (
            re.search(r"^\[tox\]", content, re.MULTILINE)
            or re.search(r"^\[testenv", content, re.MULTILINE)
            or re.search(r"^\[pkgenv", content, re.MULTILINE)
            or re.search(r"^\[base\]", content, re.MULTILINE)
        )
        else ("tox.ini", f"[testenv]\n{content}")
    )


def _wrap_tox_toml_in_pyproject(content: str) -> str:
    tox_lines: list[str] = []
    other_lines: list[str] = []
    in_tox = False
    in_other = False
    for line in content.splitlines():
        if section_match := re.match(r"^\[(?P<section>[^\]]+)\]", line):
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
        result += "\n".join(tox_lines) + "\n"
    if other_lines:
        result += "\n" + "\n".join(other_lines) + "\n"
    return result


def _find_env_names(filename: str, content: str) -> list[str]:
    envs: list[str] = []
    if filename in {"tox.toml", "pyproject.toml"}:
        if re.search(r"\[(?:tool\.tox\.)?env_base\.", content):
            return ["__env_base__"]
        for match in re.finditer(r"\[(?:tool\.tox\.)?env\.(?P<name>[^\]]+)\]", content):
            name = match.group("name").strip('"').strip("'")
            if name not in envs:
                envs.append(name)
    elif filename in {"tox.ini", "setup.cfg"}:
        for match in re.finditer(r"\[testenv:(?P<name>[^\]]+)\]", content):
            raw = match.group("name")
            if "{" not in raw and raw not in envs:
                envs.append(raw)
    return envs or ["py"]


def _should_skip(content: str) -> str | None:
    if re.search(
        r"""
        requires\s*=\s*\[?[^\]]*   # requires key with optional opening bracket
        (?:tox-uv|virtualenv[<>=!])  # matches tox-uv or virtualenv with version constraint
        """,
        content,
        re.VERBOSE | re.MULTILINE,
    ):
        return "triggers auto-provisioning"
    if re.search(
        r"""
        base_python\s*=\s*\[?\s*"?  # base_python key (not default_base_python)
        cpython3\.\d+-\d+-(?:arm64|x86_64)  # architecture-specific
        """,
        content,
        re.VERBOSE | re.MULTILINE,
    ):
        return "references architecture-specific Python"
    if re.search(r"""virtualenv_spec\s*=""", content, re.MULTILINE):
        return "requires specific virtualenv version"
    if re.search(
        r"""
        ^commands\s*=\s*\[  # commands key with list
        "[^["]              # flat string list, not nested
        """,
        content,
        re.VERBOSE | re.MULTILINE,
    ):
        return "tox output format, not input config"
    return None
