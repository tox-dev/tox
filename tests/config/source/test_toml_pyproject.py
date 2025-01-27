from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

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
