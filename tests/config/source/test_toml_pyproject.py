from __future__ import annotations

import sys
from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from tox.config.loader.replacer import MatchError

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


def test_config_in_toml_core(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
    [tool.tox]
    env_list = [ "A", "B"]

    [tool.tox.env_run_base]
    description = "Do magical things"
    commands = [
        ["python", "--version"],
        ["python", "-c", "import sys; print(sys.executable)"]
    ]
    """
    })

    outcome = project.run("c", "--core")
    outcome.assert_success()
    assert "# Exception: " not in outcome.out, outcome.out
    assert "# !!! unused: " not in outcome.out, outcome.out


def test_config_in_toml_non_default(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
    [tool.tox.env.C]
    description = "Do magical things in C"
    commands = [
        ["python", "--version"]
    ]
    """
    })

    outcome = project.run("c", "-e", "C", "--core")
    outcome.assert_success()
    assert "# Exception: " not in outcome.out, outcome.out
    assert "# !!! unused: " not in outcome.out, outcome.out


def test_config_in_toml_extra(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
    [tool.tox.env_run_base]
    description = "Do magical things"
    commands = [
        ["python", "--version"]
    ]
    """
    })

    outcome = project.run("c", "-e", ".".join(str(i) for i in sys.version_info[0:2]))
    outcome.assert_success()
    assert "# Exception: " not in outcome.out, outcome.out
    assert "# !!! unused: " not in outcome.out, outcome.out


def test_config_in_toml_explicit_mentioned(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
    [tool.tox.env_run_base]
    description = "Do magical things"
    commands = [
        ["python", "--version"]
    ]
    """
    })

    outcome = project.run("l", "-c", "pyproject.toml")
    outcome.assert_success()
    assert "could not recognize config file pyproject.toml" not in outcome.out, outcome.out


def test_config_in_toml_replace_default(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"pyproject.toml": '[tool.tox.env_run_base]\ndescription = "{missing:miss}"'})
    outcome = project.run("c", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\ndescription = miss\n", "")


def test_config_in_toml_replace_env_name_via_env(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": '[tool.tox.env_run_base]\ndescription = "Magic in {env:MAGICAL:{env_name}}"'
    })
    outcome = project.run("c", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\ndescription = Magic in py\n", "")


def test_config_in_toml_replace_env_name_via_env_set(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MAGICAL", "YEAH")
    project = tox_project({
        "pyproject.toml": '[tool.tox.env_run_base]\ndescription = "Magic in {env:MAGICAL:{env_name}}"'
    })
    outcome = project.run("c", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\ndescription = Magic in YEAH\n", "")


def test_config_in_toml_replace_from_env_section_absolute(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.A]
        description = "a"
        [tool.tox.env.B]
        description = "{[tool.tox.env.A]env_name}"
        """
    })
    outcome = project.run("c", "-e", "B", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:B]\ndescription = A\n", "")


def test_config_in_toml_replace_from_section_absolute(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.extra]
        ok = "o"
        [tool.tox.env.B]
        description = "{[tool.tox.extra]ok}"
        """
    })
    outcome = project.run("c", "-e", "B", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:B]\ndescription = o\n", "")


def test_config_in_toml_replace_from_section_absolute_nok(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox]
        extra = []
        [tool.tox.env.B]
        description = "{[tool.tox.extra.more]ok:failed}"
        """
    })
    outcome = project.run("c", "-e", "B", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err(
        "[testenv:B]\nROOT: Failed to load key more as not dictionary []\ndescription = failed\n", ""
    )


def test_config_in_toml_replace_posargs_default(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.A]
        commands = [["python", { replace = "posargs", default = ["a", "b"], extend = true } ]]
        """
    })
    outcome = project.run("c", "-e", "A", "-k", "commands")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:A]\ncommands = python a b\n", "")


def test_config_in_toml_replace_posargs_empty(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.A]
        commands = [["python", { replace = "posargs", default = ["a", "b"], extend = true } ]]
        """
    })
    outcome = project.run("c", "-e", "A", "-k", "commands", "--")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:A]\ncommands = python\n", "")


def test_config_in_toml_replace_posargs_empty_optional(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.A]
        commands = [{ replace = "posargs", default = ["a", "b"] }, ["python"]]
        """
    })
    outcome = project.run("c", "-e", "A", "-k", "commands", "--")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:A]\ncommands = python\n", "")


def test_config_in_toml_replace_posargs_set(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.A]
        commands = [["python", { replace = "posargs", default = ["a", "b"], extend = true } ]]
        """
    })
    outcome = project.run("c", "-e", "A", "-k", "commands", "--", "c", "d")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:A]\ncommands = python c d\n", "")


def test_config_in_toml_replace_env_default(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.A]
        description = { replace = "env", name = "NAME", default = "OK" }
        """
    })
    monkeypatch.delenv("NAME", raising=False)

    outcome = project.run("c", "-e", "A", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:A]\ndescription = OK\n", "")


def test_config_in_toml_replace_env_set(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.A]
        description = { replace = "env", name = "NAME", default = "OK" }
        """
    })
    monkeypatch.setenv("NAME", "OK2")

    outcome = project.run("c", "-e", "A", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:A]\ndescription = OK2\n", "")


def test_config_in_toml_replace_ref_of(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env_run_base]
        extras = ["A", "{env_name}"]
        [tool.tox.env.c]
        extras = [{ replace = "ref", of = ["tool", "tox", "env_run_base", "extras"], extend = true}, "B"]
        """
    })
    monkeypatch.setenv("NAME", "OK2")

    outcome = project.run("c", "-e", "c", "-k", "extras")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:c]\nextras =\n  a\n  b\n  c\n", "")


def test_config_in_toml_replace_ref_env(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.b]
        extras = ["{env_name}"]
        [tool.tox.env.a]
        extras = [{ replace = "ref", env = "b", "key" = "extras", extend = true }, "a"]
        """
    })
    monkeypatch.setenv("NAME", "OK2")

    outcome = project.run("c", "-e", "a", "-k", "extras")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:a]\nextras =\n  a\n  b\n", "")


def test_config_in_toml_replace_env_circular_set(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.a]
        set_env.COVERAGE_FILE = { replace = "env", name = "COVERAGE_FILE", default = "{env_name}" }
        """
    })
    monkeypatch.setenv("COVERAGE_FILE", "OK")

    outcome = project.run("c", "-e", "a", "-k", "set_env")
    outcome.assert_success()
    assert "COVERAGE_FILE=OK" in outcome.out, outcome.out


def test_config_in_toml_replace_env_circular_unset(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.a]
        set_env.COVERAGE_FILE = { replace = "env", name = "COVERAGE_FILE", default = "{env_name}" }
        """
    })
    monkeypatch.delenv("COVERAGE_FILE", raising=False)

    outcome = project.run("c", "-e", "a", "-k", "set_env")
    outcome.assert_success()
    assert "COVERAGE_FILE=a" in outcome.out, outcome.out


def test_config_in_toml_replace_fails(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.B]
        description = "{[tool.tox.extra]ok:d}"
        """
    })
    outcome = project.run("c", "-e", "B", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:B]\ndescription = d\n", "")


def test_config_in_toml_replace_from_core(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env.B]
        description = "{[tool.tox]no_package}"
        """
    })
    outcome = project.run("c", "-e", "B", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:B]\ndescription = False\n", "")


def test_config_in_toml_with_legacy(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox]
        legacy_tox_ini = '''
            [testenv]
            description=legacy
        '''
        """
    })
    outcome = project.run("c", "-e", "py", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\ndescription = legacy\n", "")


def test_config_in_toml_bad_type_env_name(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox]
        env = [1]
        """
    })
    outcome = project.run("l")
    outcome.assert_failed()
    outcome.assert_out_err("ROOT: HandledError| Environment key must be string, got 1\n", "")


def test_config_in_toml_bad_type_env(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox]
        env = {a = 1}
        """
    })
    outcome = project.run("l")
    outcome.assert_failed()
    outcome.assert_out_err("ROOT: HandledError| tool.tox.env.a must be a table, is 'int'\n", "")


def test_config_deps(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env_run_base]
        deps = ['mypy>=1', 'ruff==1']
        """
    })
    outcome = project.run("c", "-k", "deps")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\ndeps =\n  mypy>=1\n  ruff==1\n", "")


def test_config_deps_req(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env_run_base]
        deps = ['-r requirements.txt']
        """
    })
    outcome = project.run("c", "-k", "deps")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\ndeps = -r requirements.txt\n", "")


def test_config_requires(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox]
        requires = ['tox>=4']
        """
    })
    outcome = project.run("c", "-k", "requires", "--core")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py]\n\n[tox]\nrequires =\n  tox>=4\n  tox\n", "")


def test_config_set_env_ref(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env_run_base]
        set_env = { A = "1", B = "2"}
        [tool.tox.env.t]
        set_env = [
            { replace = "ref", of = ["tool", "tox", "env_run_base", "set_env"]},
            { C = "3", D = "4"},
        ]
        """
    })
    outcome = project.run("c", "-et", "-k", "set_env", "--hashseed", "1")
    outcome.assert_success()
    out = (
        "[testenv:t]\n"
        "set_env =\n"
        "  A=1\n"
        "  B=2\n"
        "  C=3\n"
        "  D=4\n"
        "  PIP_DISABLE_PIP_VERSION_CHECK=1\n"
        "  PYTHONHASHSEED=1\n"
        "  PYTHONIOENCODING=utf-8\n"
    )
    outcome.assert_out_err(out, "")


def test_config_set_env_substitution_deferred(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": """
        [env_run_base]
        package = "skip"
        set_env.COVERAGE_SRC = "{env_site_packages_dir}{/}mypackage"
        """
    })
    outcome = project.run("c", "-e", "py", "-k", "set_env")
    outcome.assert_success()
    assert "COVERAGE_SRC=" in outcome.out
    assert "mypackage" in outcome.out


def test_config_env_run_base_deps_reference_with_additional_deps(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env_run_base]
        deps = ["pytest>=8", "coverage>=7"]

        [tool.tox.env.test]
        deps = ["{[tool.tox.env_run_base]deps}", "pytest-xdist", "pytest-timeout"]
        """
    })
    outcome = project.run("c", "-e", "test", "-k", "deps")
    outcome.assert_success()
    out = "[testenv:test]\ndeps =\n  pytest>=8\n  coverage>=7\n  pytest-xdist\n  pytest-timeout\n"
    outcome.assert_out_err(out, "")


def test_config_env_pkg_base_deps_reference_with_additional_deps(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox.env_pkg_base]
        deps = ["build", "wheel"]

        [tool.tox.env.pkg]
        deps = ["{[tool.tox.env_pkg_base]deps}", "setuptools>=40"]
        """
    })
    outcome = project.run("c", "-e", "pkg", "-k", "deps")
    outcome.assert_success()
    out = "[testenv:pkg]\ndeps =\n  build\n  wheel\n  setuptools>=40\n"
    outcome.assert_out_err(out, "")


def test_config_env_base_inherit_from_arbitrary_section(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": """
        [tool.tox]
        env_list = ["a", "b"]

        [tool.tox.env.shared]
        description = "shared config"
        skip_install = true

        [tool.tox.env.a]
        base = ["shared"]

        [tool.tox.env.b]
        base = ["shared"]
        """
    })
    outcome = project.run("c", "-e", "a,b", "-k", "description")
    outcome.assert_success()
    out = "[testenv:a]\ndescription = shared config\n\n[testenv:b]\ndescription = shared config\n"
    outcome.assert_out_err(out, "")


def test_config_in_toml_replace_glob_match(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    (tmp_path / "p" / "dist").mkdir(parents=True)
    (tmp_path / "p" / "dist" / "pkg-1.0.whl").touch()
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env.A]
        description = { replace = "glob", pattern = "dist/*.whl" }
        """),
    })
    outcome = project.run("c", "-e", "A", "-k", "description")
    outcome.assert_success()
    assert "pkg-1.0.whl" in outcome.out


def test_config_in_toml_replace_glob_no_match_default(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env.A]
        description = { replace = "glob", pattern = "dist/*.xyz", default = "none" }
        """),
    })
    outcome = project.run("c", "-e", "A", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:A]\ndescription = none\n", "")


def test_config_in_toml_replace_glob_extend(tox_project: ToxProjectCreator, tmp_path: Path) -> None:
    (tmp_path / "p" / "dist").mkdir(parents=True)
    (tmp_path / "p" / "dist" / "a.whl").touch()
    (tmp_path / "p" / "dist" / "b.whl").touch()
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env.A]
        commands = [["echo", { replace = "glob", pattern = "dist/*.whl", extend = true }]]
        """),
    })
    outcome = project.run("c", "-e", "A", "-k", "commands")
    outcome.assert_success()
    assert "a.whl" in outcome.out
    assert "b.whl" in outcome.out


@pytest.mark.parametrize(
    ("env_vars", "condition", "then", "else_val", "expected"),
    [
        pytest.param({"TAG": "v1"}, "env.TAG", "yes", "no", "yes", id="env_set"),
        pytest.param({}, "env.TAG", "yes", "no", "no", id="env_unset"),
        pytest.param({"TAG": ""}, "env.TAG", "yes", "no", "no", id="env_empty"),
        pytest.param({"CI": "true"}, "env.CI == 'true'", "ci", "local", "ci", id="eq_match"),
        pytest.param({"CI": "false"}, "env.CI == 'true'", "ci", "local", "local", id="eq_no_match"),
        pytest.param({"M": "s"}, "env.M != 'prod'", "dev", "prod", "dev", id="neq"),
        pytest.param({"CI": "1", "D": "1"}, "env.CI and env.D", "y", "n", "y", id="and_true"),
        pytest.param({"CI": "1"}, "env.CI and env.D", "y", "n", "n", id="and_partial"),
        pytest.param({}, "env.CI or env.L", "y", "n", "n", id="or_false"),
        pytest.param({"L": "1"}, "env.CI or env.L", "y", "n", "y", id="or_true"),
        pytest.param({}, "not env.CI", "local", "ci", "local", id="not_true"),
        pytest.param({"CI": "1"}, "not env.CI", "local", "ci", "ci", id="not_false"),
    ],
)
def test_config_in_toml_replace_if(  # noqa: PLR0913
    tox_project: ToxProjectCreator,
    monkeypatch: pytest.MonkeyPatch,
    env_vars: dict[str, str],
    condition: str,
    then: str,
    else_val: str,
    expected: str,
) -> None:
    for k in ("TAG", "CI", "D", "L", "M"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    project = tox_project({
        "pyproject.toml": dedent(f"""
        [tool.tox.env.A]
        description = {{ replace = "if", condition = "{condition}", then = "{then}", else = "{else_val}" }}
        """),
    })
    outcome = project.run("c", "-e", "A", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err(f"[testenv:A]\ndescription = {expected}\n", "")


def test_config_in_toml_replace_if_no_else(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEPLOY", raising=False)
    project = tox_project({
        "pyproject.toml": """\
        [tool.tox.env.A]
        description = { replace = "if", condition = "env.DEPLOY", then = "deploy mode" }
        """
    })
    outcome = project.run("c", "-e", "A", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:A]\ndescription = \n", "")


def test_config_in_toml_replace_if_nested_substitution(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEPLOY", "yes")
    project = tox_project({
        "pyproject.toml": """\
        [tool.tox.env.A]
        description = { replace = "if", condition = "env.DEPLOY", then = "{env_name}", else = "none" }
        """
    })
    outcome = project.run("c", "-e", "A", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:A]\ndescription = A\n", "")


def test_config_in_toml_replace_if_set_env(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAG_NAME", "v2.0")
    project = tox_project({
        "pyproject.toml": """\
        [tool.tox.env.A]
        set_env.MATURITY = { replace = "if", condition = "env.TAG_NAME", then = "production", else = "testing" }
        """
    })
    outcome = project.run("c", "-e", "A", "-k", "set_env")
    outcome.assert_success()
    assert "MATURITY=production" in outcome.out


def test_config_in_toml_replace_if_extend(tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("V", "1")
    toml = """\
    [tool.tox.env.A]
    commands = [["echo", { replace = "if", condition = "env.V", then = ["-v"], else = ["-q"], extend = true }]]
    """
    project = tox_project({"pyproject.toml": toml})
    outcome = project.run("c", "-e", "A", "-k", "commands")
    outcome.assert_success()
    assert "-v" in outcome.out


@pytest.mark.parametrize(
    ("condition_toml", "error_match"),
    [
        pytest.param(
            'then = "yes", else = "no"',
            "No condition was supplied in if replacement",
            id="missing_condition",
        ),
        pytest.param(
            'condition = "env.CI", else = "no"',
            "No 'then' value was supplied in if replacement",
            id="missing_then",
        ),
        pytest.param(
            'condition = "env.CI ===", then = "yes"',
            r"Invalid condition expression: env\.CI ===",
            id="invalid_syntax",
        ),
        pytest.param(
            'condition = "env.CI > env.X", then = "yes"',
            r"Unsupported comparison operator in condition: env\.CI > env\.X",
            id="unsupported_compare",
        ),
        pytest.param(
            'condition = "1 + 2", then = "yes"',
            r"Unsupported expression in condition: ",
            id="unsupported_expr",
        ),
    ],
)
def test_config_in_toml_replace_if_error(tox_project: ToxProjectCreator, condition_toml: str, error_match: str) -> None:
    project = tox_project({
        "pyproject.toml": dedent(f"""
        [tool.tox.env.A]
        description = {{ replace = "if", {condition_toml} }}
        """),
    })
    with pytest.raises(MatchError, match=error_match):
        project.run("c", "-e", "A", "-k", "description")


def test_config_in_toml_replace_if_factor_positive(tox_project: ToxProjectCreator) -> None:

    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env."3.13-django50"]
        description = { replace = "if", condition = "factor.django50", then = "has django50", else = "no django50" }
        """),
    })
    outcome = project.run("c", "-e", "3.13-django50", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:3.13-django50]\ndescription = has django50\n", "")


def test_config_in_toml_replace_if_factor_negative(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env."3.13"]
        description = { replace = "if", condition = "factor.django50", then = "has django50", else = "no django50" }
        """),
    })
    outcome = project.run("c", "-e", "3.13", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:3.13]\ndescription = no django50\n", "")


def test_config_in_toml_replace_if_factor_platform(tox_project: ToxProjectCreator) -> None:
    condition_val = f"factor.{sys.platform}"
    toml_str = f"""
        [tool.tox.env.task]
        description.replace = "if"
        description.condition = "{condition_val}"
        description.then = "correct platform"
        description.else = "wrong platform"
        """
    project = tox_project({"pyproject.toml": dedent(toml_str)})
    outcome = project.run("c", "-e", "task", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:task]\ndescription = correct platform\n", "")


def test_config_in_toml_replace_if_factor_not(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env."3.13"]
        description = { replace = "if", condition = "not factor.win32", then = "not windows", else = "windows" }
        """),
    })
    outcome = project.run("c", "-e", "3.13", "-k", "description")
    outcome.assert_success()
    expected = "windows" if sys.platform == "win32" else "not windows"
    outcome.assert_out_err(f"[testenv:3.13]\ndescription = {expected}\n", "")


def test_config_in_toml_replace_if_factor_and(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env.py313-django50]
        description.replace = "if"
        description.condition = "factor.django50 and factor.py313"
        description.then = "both"
        description.else = "not both"
        """),
    })
    outcome = project.run("c", "-e", "py313-django50", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py313-django50]\ndescription = both\n", "")


def test_config_in_toml_replace_if_factor_or(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env.py313]
        description.replace = "if"
        description.condition = "factor.django50 or factor.py313"
        description.then = "at least one"
        description.else = "neither"
        """),
    })
    outcome = project.run("c", "-e", "py313", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:py313]\ndescription = at least one\n", "")


def test_config_in_toml_replace_if_factor_combined_with_env(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI", "1")
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env."3.13-django50"]
        description.replace = "if"
        description.condition = "factor.django50 and env.CI"
        description.then = "django in CI"
        description.else = "other"
        """),
    })
    outcome = project.run("c", "-e", "3.13-django50", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:3.13-django50]\ndescription = django in CI\n", "")


def test_config_in_toml_replace_if_list_without_extend_in_deps(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("X", "1")
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env_run_base]
        deps = [
            "pytest",
            { replace = "if", condition = "env.X", then = ["extra-pkg"] },
        ]
        """),
    })
    outcome = project.run("c", "-e", "py", "-k", "deps")
    outcome.assert_failed()
    assert "failed to load py.deps: deps expected str, list[str], or list[Requirement]" in outcome.out


def test_config_in_toml_replace_if_list_with_extend(
    tox_project: ToxProjectCreator, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("X", "1")
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env_run_base]
        deps = [
            "pytest",
            { replace = "if", condition = "env.X", then = ["extra-pkg"], extend = true },
        ]
        """),
    })
    outcome = project.run("c", "-e", "py", "-k", "deps")
    outcome.assert_success()
    assert "extra-pkg" in outcome.out


_CMD = 'commands = [["python", "--version"]]'


@pytest.mark.parametrize(
    ("toml_body", "key", "expected_msg"),
    [
        # --- str fields ---
        pytest.param(f"description = 1\n{_CMD}", "description", "1 is not of type 'str'", id="description-int"),
        pytest.param(f"platform = 1\n{_CMD}", "platform", "1 is not of type 'str'", id="platform-int"),
        pytest.param(f"runner = 1\n{_CMD}", "runner", "1 is not of type 'str'", id="runner-int"),
        pytest.param(f"package = 1\n{_CMD}", "package", "1 is not of type 'str'", id="package-int"),
        pytest.param(f"pylock = 1\n{_CMD}", "pylock", "1 is not of type 'str'", id="pylock-int"),
        pytest.param(f"virtualenv_spec = 1\n{_CMD}", "virtualenv_spec", "1 is not of type 'str'", id="venv-spec-int"),
        # --- bool fields ---
        pytest.param(f"ignore_errors = 42\n{_CMD}", "ignore_errors", "42 is not of type 'bool'", id="ignore-err-int"),
        pytest.param(
            f"parallel_show_output = 42\n{_CMD}", "parallel_show_output", "42 is not of type 'bool'", id="parallel-int"
        ),
        pytest.param(f"recreate = 42\n{_CMD}", "recreate", "42 is not of type 'bool'", id="recreate-int"),
        pytest.param(
            f"args_are_paths = 42\n{_CMD}", "args_are_paths", "42 is not of type 'bool'", id="args-are-paths-int"
        ),
        pytest.param(
            f"ignore_outcome = 42\n{_CMD}", "ignore_outcome", "42 is not of type 'bool'", id="ignore-outcome-int"
        ),
        pytest.param(f"fail_fast = 42\n{_CMD}", "fail_fast", "42 is not of type 'bool'", id="fail-fast-int"),
        pytest.param(f"skip_install = 42\n{_CMD}", "skip_install", "42 is not of type 'bool'", id="skip-install-int"),
        pytest.param(f"use_develop = 42\n{_CMD}", "use_develop", "42 is not of type 'bool'", id="use-develop-int"),
        pytest.param(
            f"system_site_packages = 42\n{_CMD}",
            "system_site_packages",
            "42 is not of type 'bool'",
            id="sys-site-pkg-int",
        ),
        pytest.param(f"always_copy = 42\n{_CMD}", "always_copy", "42 is not of type 'bool'", id="always-copy-int"),
        pytest.param(f"download = 42\n{_CMD}", "download", "42 is not of type 'bool'", id="download-int"),
        pytest.param(f"pip_pre = 42\n{_CMD}", "pip_pre", "42 is not of type 'bool'", id="pip-pre-int"),
        pytest.param(
            f"constrain_package_deps = 42\n{_CMD}",
            "constrain_package_deps",
            "42 is not of type 'bool'",
            id="constrain-pkg-deps-int",
        ),
        pytest.param(
            f"use_frozen_constraints = 42\n{_CMD}",
            "use_frozen_constraints",
            "42 is not of type 'bool'",
            id="frozen-constraints-int",
        ),
        pytest.param(
            f"skip_missing_interpreters = 42\n{_CMD}",
            "skip_missing_interpreters",
            "42 is not of type 'bool'",
            id="skip-missing-int",
        ),
        # --- int fields ---
        pytest.param(
            f'commands_retry = "bad"\n{_CMD}',
            "commands_retry",
            "invalid literal for int() with base 10: 'bad'",
            id="cmd-retry-str",
        ),
        # --- float fields ---
        pytest.param(
            f'suicide_timeout = "bad"\n{_CMD}',
            "suicide_timeout",
            "could not convert string to float: 'bad'",
            id="suicide-str",
        ),
        pytest.param(
            f'interrupt_timeout = "bad"\n{_CMD}',
            "interrupt_timeout",
            "could not convert string to float: 'bad'",
            id="interrupt-str",
        ),
        pytest.param(
            f'terminate_timeout = "bad"\n{_CMD}',
            "terminate_timeout",
            "could not convert string to float: 'bad'",
            id="terminate-str",
        ),
        # --- Path fields ---
        pytest.param(f"env_dir = 1\n{_CMD}", "env_dir", "1 is not of type 'str'", id="env-dir-int"),
        pytest.param(f"env_tmp_dir = 1\n{_CMD}", "env_tmp_dir", "1 is not of type 'str'", id="env-tmp-dir-int"),
        pytest.param(f"env_log_dir = 1\n{_CMD}", "env_log_dir", "1 is not of type 'str'", id="env-log-dir-int"),
        pytest.param(f"change_dir = 1\n{_CMD}", "change_dir", "1 is not of type 'str'", id="change-dir-int"),
        # --- list[str] fields ---
        pytest.param(f"pass_env = 42\n{_CMD}", "pass_env", "42 is not list", id="pass-env-not-list"),
        pytest.param(f"pass_env = [1]\n{_CMD}", "pass_env", "1 is not of type 'str'", id="pass-env-int-item"),
        pytest.param(
            f"disallow_pass_env = 42\n{_CMD}", "disallow_pass_env", "42 is not list", id="disallow-pass-env-not-list"
        ),
        pytest.param(
            f"allowlist_externals = [true]\n{_CMD}",
            "allowlist_externals",
            "True is not of type 'str'",
            id="allowlist-bool-item",
        ),
        pytest.param(
            f"base_python = 42\n{_CMD}",
            "base_python",
            "42 cannot cast to list[str] | str",
            id="base-python-not-list",
        ),
        # --- set[str] fields ---
        pytest.param(f"labels = 42\n{_CMD}", "labels", "42 is not list", id="labels-not-list"),
        pytest.param(f"labels = [1]\n{_CMD}", "labels", "1 is not of type 'str'", id="labels-int-item"),
        pytest.param(f"extras = 42\n{_CMD}", "extras", "42 is not list", id="extras-not-list"),
        pytest.param(
            f"dependency_groups = 42\n{_CMD}", "dependency_groups", "42 is not list", id="dep-groups-not-list"
        ),
        # --- list[Command] fields ---
        pytest.param("commands = 42", "commands", "42 is not list", id="commands-not-list"),
        pytest.param("commands = [[1]]", "commands", "1 is not of type 'str'", id="commands-int-arg"),
        pytest.param("commands_pre = 42", "commands_pre", "42 is not list", id="commands-pre-not-list"),
        pytest.param("commands_post = 42", "commands_post", "42 is not list", id="commands-post-not-list"),
        pytest.param(
            "recreate_commands = [[1]]", "recreate_commands", "1 is not of type 'str'", id="recreate-cmds-int-arg"
        ),
        pytest.param(
            "extra_setup_commands = 42", "extra_setup_commands", "42 is not list", id="extra-setup-cmds-not-list"
        ),
        # --- EnvList fields ---
        pytest.param(f"depends = 42\n{_CMD}", "depends", "env_list must be a list, got int", id="depends-not-list"),
        pytest.param(
            f"depends = [1]\n{_CMD}",
            "depends",
            "env_list items must be strings or product dicts, got int",
            id="depends-int-item",
        ),
        # --- factory fields ---
        pytest.param("deps = [1]", "deps", "deps expected str, list[str], or list[Requirement]", id="deps-int-item"),
        pytest.param("deps = true", "deps", "deps expected str, list[str], or list[Requirement]", id="deps-bool"),
        pytest.param(
            f"constraints = 42\n{_CMD}",
            "constraints",
            "constraints expected str, list[str], or list[Requirement]",
            id="constraints-int",
        ),
    ],
)
def test_config_in_toml_type_error_message(
    tox_project: ToxProjectCreator,
    toml_body: str,
    key: str,
    expected_msg: str,
) -> None:
    project = tox_project({
        "pyproject.toml": dedent(f"""
        [tool.tox.env_run_base]
        {toml_body}
        """),
    })
    outcome = project.run("c", "-e", "py", "-k", key)
    outcome.assert_failed()
    assert f"failed to load py.{key}" in outcome.out
    assert expected_msg in outcome.out


def test_config_in_toml_handled_error_on_run(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": dedent("""
        [tool.tox.env_run_base]
        deps = [1]
        commands = [["python", "--version"]]
        """),
    })
    outcome = project.run("r", "-e", "py")
    outcome.assert_failed()
    assert "internal error" not in outcome.out
    assert "failed to load py.deps" in outcome.out
    assert "deps expected str, list[str], or list[Requirement]" in outcome.out
