from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator

_DOCS_DIR = Path(__file__).parents[2] / "docs"

_CODE_BLOCK_RE = re.compile(r"^(\s*)\.\.(\s+)code-block::\s+(toml|ini)\s*$")

_SKIP_TOML_SECTIONS = frozenset({
    "build-system",
    "project",
    "project.entry-points.tox",
    "project.optional-dependencies",
})

_REQUIRES_PROVISION_RE = re.compile(
    r"""requires\s*=\s*\[?[^\]]*(?:tox-uv|virtualenv[<>=!])""",
    re.MULTILINE,
)
_BASE_PYTHON_UNAVAILABLE_RE = re.compile(
    r"""base_python\s*=\s*\[?\s*"?(?:python3\.[0-9]\b|python3\.1[5-9]\b|cpython3\.\d+-\d+-(?:arm64|x86_64))""",
    re.MULTILINE,
)
_VIRTUALENV_SPEC_RE = re.compile(r"""virtualenv_spec\s*=""", re.MULTILINE)
_COMMANDS_FLAT_LIST_RE = re.compile(r"""^commands\s*=\s*\["[^["]""", re.MULTILINE)

_DOC_ENV_VARS: dict[str, str] = {
    "CI": "1",
    "TAG_NAME": "v1.0",
    "VERBOSE": "1",
    "DEBUG": "1",
    "DEPLOY": "1",
    "LOCAL": "1",
    "L": "1",
    "X": "1",
    "MODE": "dev",
}


def _wrap_tox_toml_in_pyproject(content: str) -> str:
    tox_lines: list[str] = []
    other_lines: list[str] = []
    in_tox = False
    in_other = False
    for line in content.splitlines():
        if section_match := re.match(r"^\[([^\]]+)\]", line):
            section = section_match.group(1)
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


def _classify(lang: str, content: str) -> tuple[str, str]:
    if lang == "ini":
        return _classify_ini(content)
    if "legacy_tox_ini" in content:
        if not re.search(r"^\[tool\.tox\]", content, re.MULTILINE):
            return "pyproject.toml", f"[tool.tox]\n{content}"
        return "pyproject.toml", content
    if re.search(r"^\[tool\.tox", content, re.MULTILINE):
        return "pyproject.toml", content
    if re.search(r"^\[dependency-groups\]", content, re.MULTILINE):
        return "pyproject.toml", _wrap_tox_toml_in_pyproject(content)
    return "tox.toml", content


def _extract_config_blocks() -> list[tuple[str, int, str, str]]:
    results: list[tuple[str, int, str, str]] = []
    for rst_path in sorted(_DOCS_DIR.rglob("*.rst")):
        lines = rst_path.read_text(encoding="utf-8").splitlines()
        idx = 0
        while idx < len(lines):
            if match := _CODE_BLOCK_RE.match(lines[idx]):
                directive_indent = len(match.group(1)) + len(match.group(2)) + 2
                lang = match.group(3)
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
                        str(rst_path.relative_to(_DOCS_DIR.parent)),
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
    first_section = re.search(r"^\[([^\]]+)\]", content, re.MULTILINE)
    if first_section and first_section.group(1).split(".")[0].strip('"').strip("'") in _SKIP_TOML_SECTIONS:
        return False
    return bool(
        "legacy_tox_ini" in content
        or re.search(r"^\[tool\.tox", content, re.MULTILINE)
        or re.search(r"^\[(env|env_run_base|env_pkg_base|env_base)\b", content, re.MULTILINE)
        or re.search(r"^env_list\s*=", content, re.MULTILINE)
        or re.search(r"^(requires|no_package)\s*=", content, re.MULTILINE)
        or (re.search(r"^\w+\s*=", content, re.MULTILINE) and not first_section)
    )


def _should_skip(content: str) -> str | None:
    if _REQUIRES_PROVISION_RE.search(content):
        return "triggers auto-provisioning"
    if _BASE_PYTHON_UNAVAILABLE_RE.search(content):
        return "references unavailable Python interpreter"
    if _VIRTUALENV_SPEC_RE.search(content):
        return "requires specific virtualenv version"
    if _COMMANDS_FLAT_LIST_RE.search(content):
        return "tox output format, not input config"
    return None


def _find_env_names(filename: str, content: str) -> list[str]:
    envs: list[str] = []
    if filename in {"tox.toml", "pyproject.toml"}:
        if re.search(r"\[(?:tool\.tox\.)?env_base\.", content):
            return ["__env_base__"]
        for match in re.finditer(r"\[(?:tool\.tox\.)?env\.([^\]]+)\]", content):
            name = match.group(1).strip('"').strip("'")
            if name not in envs:
                envs.append(name)
    elif filename in {"tox.ini", "setup.cfg"}:
        for match in re.finditer(r"\[testenv:([^\]]+)\]", content):
            raw = match.group(1)
            if "{" not in raw and raw not in envs:
                envs.append(raw)
    return envs or ["py"]


def _collect_params() -> list[pytest.param]:  # type: ignore[type-arg]
    params: list[pytest.param] = []  # type: ignore[type-arg]
    for rel_file, line_no, lang, content in _extract_config_blocks():
        if not _is_tox_config(lang, content):
            continue
        filename, classified_content = _classify(lang, content)
        env_names = _find_env_names(filename, classified_content)
        marks: list[pytest.MarkDecorator] = []
        if skip_reason := _should_skip(classified_content):
            marks.append(pytest.mark.skip(reason=skip_reason))
        params.append(pytest.param(filename, classified_content, env_names, id=f"{rel_file}:{line_no}", marks=marks))
    return params


@pytest.mark.parametrize(("filename", "content", "env_names"), _collect_params())
def test_doc_config_valid(
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content: str,
    env_names: list[str],
) -> None:
    for key, value in _DOC_ENV_VARS.items():
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
