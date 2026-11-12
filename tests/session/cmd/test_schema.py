from __future__ import annotations

import json
import re
import shutil
import subprocess
import sysconfig
from collections.abc import Mapping, Sequence
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Final, NamedTuple, Protocol

import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

    from tox.pytest import MonkeyPatch, ToxProjectCreator
    from tox.util.json_types import JsonValue


class LintWorkspace(Protocol):
    def __call__(self, filename: str, content: str, tombi_cfg: str = ...) -> None: ...


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return Path(__file__).parents[3]


@pytest.fixture(scope="session")
def schema_path(repo_root: Path) -> Path:
    return repo_root / "src" / "tox" / "tox.schema.json"


@pytest.fixture(scope="session")
def replace_py(repo_root: Path) -> Path:
    return repo_root / "src" / "tox" / "config" / "loader" / "toml" / "_replace.py"


@pytest.fixture(scope="session")
def default_tombi_cfg() -> str:
    # empty catalog: tombi's bundled pyproject.json schema $refs an external partial-tox.json it cannot
    # fetch under --offline, so leaving the default catalog on turns that miss into an error-on-warnings failure
    return dedent("""\
        [schema.catalog]
        paths = []

        [[schemas]]
        path = "tox.schema.json"
        include = ["tox.toml"]
    """)


@pytest.fixture(scope="session")
def committed_schema(
    schema_path: Path,
) -> dict[str, Any]:  # simplint: ignore[imprecise-annotation]  # the committed schema has any JSON shape
    return json.loads(schema_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def implemented_replace_types(replace_py: Path) -> set[str]:
    # Replace tokens parsed out of the loader implementation.
    return set(re.findall(r'replace_type == "([a-z]+)"', replace_py.read_text(encoding="utf-8")))


@pytest.fixture(scope="session")
def replace_form_content() -> dict[str, str]:
    # Each replace form rendered as a minimal `tox.toml` snippet that exercises it.
    return {
        "env": dedent("""\
            [env_run_base]
            deps = [{ replace = "env", name = "DEPS_PIN", default = "pytest" }]
        """),
        "ref": dedent("""\
            [env_run_base]
            deps = [{ replace = "ref", of = ["env_run_base", "deps"] }]
        """),
        "posargs": dedent("""\
            [env_run_base]
            commands = [["pytest", { replace = "posargs", default = ["tests"], substitute = true }]]
        """),
        "glob": dedent("""\
            [env_run_base]
            deps = [{ replace = "glob", pattern = "requirements*.txt", extend = true }]
        """),
        "if": dedent("""\
            [env_run_base]
            commands = [
              { replace = "if", condition = "env.CI", then = [["ruff", "check"]], extend = true },
              ["pytest"],
            ]
        """),
    }


@pytest.fixture
def tombi_bin() -> str:
    # the test group installs tombi beside the interpreter, whose scripts directory is on PATH only inside tox run
    tombi: Final[str | None] = shutil.which("tombi", path=sysconfig.get_path("scripts"))
    assert tombi is not None, "tombi must be installed (declared in the test dependency group)"
    return tombi


@pytest.fixture
def lint_workspace(tmp_path: Path, tombi_bin: str, schema_path: Path, default_tombi_cfg: str) -> LintWorkspace:
    # Stage a tox config + the committed schema and assert `tombi lint` succeeds.
    def _run(filename: str, content: str, tombi_cfg: str = default_tombi_cfg) -> None:
        shutil.copy2(schema_path, tmp_path / "tox.schema.json")
        (tmp_path / filename).write_text(content)
        (tmp_path / "tombi.toml").write_text(tombi_cfg)
        result = subprocess.run(
            [tombi_bin, "lint", "--error-on-warnings", "--offline", filename],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    return _run


def test_show_schema_empty_dir(tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    schema = json.loads(tox_project({}).run("-qq", "schema").out)
    assert "properties" in schema
    assert "tox_root" in schema["properties"]


def test_schema_freshness(
    tox_project: ToxProjectCreator,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    committed_schema: dict[
        str, Any  # simplint: ignore[imprecise-annotation]  # the committed schema has any JSON shape
    ],
) -> None:
    monkeypatch.chdir(tmp_path)
    project = tox_project({
        "tox.toml": 'env_list = ["py"]',
        "pyproject.toml": '[build-system]\nrequires = ["setuptools"]\nbuild-backend = "setuptools.build_meta"',
    })
    generated = json.loads(project.run("-qq", "schema").out)
    assert generated == committed_schema, (
        "tox.schema.json is out of date — regenerate with: tox schema > src/tox/tox.schema.json"
    )


def test_schema_required_properties_are_declared(committed_schema: Mapping[str, JsonValue]) -> None:
    # ajv strict mode, which SchemaStore runs, rejects a required property the schema never declares; catching that
    # here beats hearing it from a release sync (tox-dev/tox#4051)
    undeclared = {
        pointer: sorted(set(schema.get("required", [])) - set(schema.get("properties", {})))
        for pointer, schema in _subschemas(committed_schema)
    }
    assert {pointer: names for pointer, names in undeclared.items() if names} == {}


def _subschemas(node: JsonValue, pointer: str = "#") -> Iterator[tuple[str, Mapping[str, JsonValue]]]:
    if isinstance(node, Mapping):
        yield pointer, node
        for key, value in node.items():
            yield from _subschemas(value, f"{pointer}/{key}")
    elif isinstance(node, Sequence) and not isinstance(node, str):
        for index, value in enumerate(node):
            yield from _subschemas(value, f"{pointer}/{index}")


def test_schema_allows_deps_array(
    committed_schema: dict[
        str, Any  # simplint: ignore[imprecise-annotation]  # the committed schema has any JSON shape
    ],
) -> None:
    deps_schema = committed_schema["properties"]["env_run_base"]["properties"]["deps"]

    assert {"type": "string"} in deps_schema["oneOf"]
    assert {"type": "array", "items": {"$ref": "#/definitions/subs"}} in deps_schema["oneOf"]


class _LintCase(NamedTuple):
    filename: str
    content: str
    tombi_cfg: str


@pytest.fixture
def project_lint_case(request: pytest.FixtureRequest, repo_root: Path, default_tombi_cfg: str) -> _LintCase:
    # Resolve a parametrized lint case (`filename`, `content`, `tombi_cfg`) by id.
    if request.param == "tox.toml":
        return _LintCase("tox.toml", (repo_root / "tox.toml").read_text(), default_tombi_cfg)
    if request.param == "pyproject.toml":
        cfg = dedent("""\
            [schema.catalog]
            paths = []

            [[schemas]]
            root = "tool.tox"
            path = "tox.schema.json"
            include = ["pyproject.toml"]
        """)
        content = dedent("""\
            [tool.tox]
            requires = ['tox>=4']
            env_list = ['py']
            skip_missing_interpreters = true

            [tool.tox.env_run_base]
            commands = [['pytest']]
            deps = ['pytest', '-r requirements.txt']

            [tool.tox.env.lint]
            commands = [['ruff', 'check', '.']]
        """)
        return _LintCase("pyproject.toml", content, cfg)
    raise ValueError(request.param)


@pytest.mark.parametrize(
    "project_lint_case",
    [pytest.param("tox.toml", id="tox.toml"), pytest.param("pyproject.toml", id="pyproject.toml")],
    indirect=True,
)
def test_schema_tombi_lint(lint_workspace: LintWorkspace, project_lint_case: _LintCase) -> None:
    filename, content, tombi_cfg = project_lint_case
    lint_workspace(filename, content, tombi_cfg)


def test_schema_covers_every_replace_type(
    committed_schema: dict[
        str, Any  # simplint: ignore[imprecise-annotation]  # the committed schema has any JSON shape
    ],
    implemented_replace_types: set[str],
    replace_form_content: dict[str, str],
) -> None:
    # Guard: every ``replace_type == "..."`` in _replace.py needs a schema variant.
    #
    # Catches the failure mode behind issue #3939, where a new replace form (``if``) was added to the loader but never
    # wired into the JSON schema.
    in_schema = {
        name.removeprefix("replace_") for name in committed_schema["definitions"] if name.startswith("replace_")
    } - {"object"}
    assert implemented_replace_types == in_schema, (
        f"replace types in loader {implemented_replace_types} differ from schema definitions {in_schema}; "
        f"update src/tox/session/cmd/schema.py and regenerate tox.schema.json"
    )
    assert implemented_replace_types == set(replace_form_content), (
        f"replace types in loader {implemented_replace_types} differ from tombi-lint fixtures "
        f"{set(replace_form_content)}; add a sample to the replace_form_content fixture"
    )


@pytest.mark.parametrize(
    "replace_form",
    [
        pytest.param("env", id="env"),
        pytest.param("ref", id="ref"),
        pytest.param("posargs", id="posargs"),
        pytest.param("glob", id="glob"),
        pytest.param("if", id="if"),
    ],
)
def test_schema_tombi_lint_replace_forms(
    lint_workspace: LintWorkspace, replace_form_content: dict[str, str], replace_form: str
) -> None:
    lint_workspace("tox.toml", replace_form_content[replace_form])
