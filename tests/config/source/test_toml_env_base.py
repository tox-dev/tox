from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_env_base_simple_factors(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.task]
            factors = ["x", "y"]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    assert "task-x" in result.out
    assert "task-y" in result.out


def test_env_base_cartesian_product(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.task]
            factors = [["a", "b"], ["x", "y"]]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    for env in ("task-a-x", "task-a-y", "task-b-x", "task-b-y"):
        assert env in result.out


def test_env_base_range_factors(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.task]
            factors = [{"prefix" = "py3", "start" = 12, "stop" = 13}]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    assert "task-py312" in result.out
    assert "task-py313" in result.out


def test_env_base_config_inheritance(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.lib]
            factors = ["a", "b"]
            package = "skip"
            description = "from env_base"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    outcome = project.run("c", "-e", "lib-a", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:lib-a]\ndescription = from env_base\n", "")


def test_env_base_inherits_from_env_run_base(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_run_base]
            description = "from run_base"

            [env_base.lib]
            factors = ["a"]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    outcome = project.run("c", "-e", "lib-a", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:lib-a]\ndescription = from run_base\n", "")


def test_env_base_factor_conditionals(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.django]
            factors = [["a", "b"], ["py314", "py315"]]
            package = "skip"
            description = {replace = "if", condition = "factor.py315", then = "uses315", else = "uses314"}
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    outcome = project.run("c", "-e", "django-a-py314", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:django-a-py314]\ndescription = uses314\n", "")
    outcome = project.run("c", "-e", "django-b-py315", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:django-b-py315]\ndescription = uses315\n", "")


def test_env_base_template_not_listed(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.lib]
            factors = ["a", "b"]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    lines = result.out.splitlines()
    env_names = [line.split()[0] for line in lines if line.strip() and " -> " in line]
    assert "lib" not in env_names


def test_env_base_explicit_env_override(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.lib]
            factors = ["a", "b"]
            package = "skip"
            description = "from base"
            commands = [["python", "-c", "print('ok')"]]

            [env.lib-a]
            description = "overridden"
        """),
    })
    outcome = project.run("c", "-e", "lib-a", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:lib-a]\ndescription = overridden\n", "")
    outcome = project.run("c", "-e", "lib-b", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:lib-b]\ndescription = from base\n", "")


def test_env_base_multiple_entries(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.lib]
            factors = ["a"]
            package = "skip"
            commands = [["python", "-c", "print('lib')"]]

            [env_base.app]
            factors = ["x"]
            package = "skip"
            commands = [["python", "-c", "print('app')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    assert "lib-a" in result.out
    assert "app-x" in result.out


def test_env_base_no_unused_warnings(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.lib]
            factors = ["a"]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    outcome = project.run("c", "-e", "lib-a")
    outcome.assert_success()
    assert "# !!! unused: " not in outcome.out


def test_env_base_generated_envs_can_run(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.task]
            factors = ["a"]
            package = "skip"
            commands = [["python", "-c", "print('hello')"]]
        """),
    })
    result = project.run("r", "-e", "task-a")
    result.assert_success()
    assert "hello" in result.out


def test_env_base_pyproject_toml(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "pyproject.toml": textwrap.dedent("""\
            [tool.tox.env_base.lib]
            factors = ["a", "b"]
            package = "skip"
            description = "pyproject"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    outcome = project.run("c", "-e", "lib-a", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:lib-a]\ndescription = pyproject\n", "")


def test_env_base_missing_factors(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.lib]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_failed()
    assert "env_base.lib requires a 'factors' key; use [env.lib] for single environments" in result.out


def test_env_base_factors_not_a_list(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.lib]
            factors = "bad"
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_failed()
    assert "env_base.lib.factors must be a list" in result.out


def test_env_base_env_run_base_override_order(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_run_base]
            description = "from run_base"

            [env_base.lib]
            factors = ["a"]
            package = "skip"
            description = "from env_base"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    outcome = project.run("c", "-e", "lib-a", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:lib-a]\ndescription = from env_base\n", "")


def test_env_base_core_no_unused_warning(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.lib]
            factors = ["a"]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    outcome = project.run("c", "--core")
    outcome.assert_success()
    assert "# !!! unused: " not in outcome.out


def test_env_base_deps_from_template(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.lib]
            factors = ["a"]
            package = "skip"
            deps = ["pytest>=8", "coverage"]
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    outcome = project.run("c", "-e", "lib-a", "-k", "deps")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:lib-a]\ndeps =\n  pytest>=8\n  coverage\n", "")


def test_env_base_doc_getting_started_scaling(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.test]
            factors = [["3.13", "3.14"]]
            deps = ["pytest>=8"]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    assert "test-3.13" in result.out
    assert "test-3.14" in result.out


def test_env_base_doc_reference_generative(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.build]
            factors = [["py312", "py313"], ["x86", "x64"]]
            package = "skip"
            env_dir = {replace = "if", condition = "factor.x86", then = ".venv-x86", else = ".venv-x64"}
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    for env in ("build-py312-x86", "build-py312-x64", "build-py313-x86", "build-py313-x64"):
        assert env in result.out


def test_env_base_doc_reference_django_matrix(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.django]
            factors = [["py312", "py313"], ["django42", "django50"]]
            package = "skip"
            deps = [
                "pytest",
                {replace = "if", condition = "factor.django42", then = ["Django>=4.2,<4.3"]},
                {replace = "if", condition = "factor.django50", then = ["Django>=5.0,<5.1"]},
            ]
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    for env in ("django-py312-django42", "django-py312-django50", "django-py313-django42", "django-py313-django50"):
        assert env in result.out


def test_env_base_doc_howto_matrix(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.django]
            factors = [
                {"prefix" = "py3", "start" = 13, "stop" = 14},
                ["django42", "django50"],
            ]
            package = "skip"
            deps = [
                "pytest",
                {replace = "if", condition = "factor.django42", then = ["Django>=4.2,<4.3"]},
                {replace = "if", condition = "factor.django50", then = ["Django>=5.0,<5.1"]},
            ]
            commands = [["pytest"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    for env in ("django-py313-django42", "django-py313-django50", "django-py314-django42", "django-py314-django50"):
        assert env in result.out


def test_env_base_doc_howto_override(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.django]
            factors = [
                {"prefix" = "py3", "start" = 13, "stop" = 14},
                ["django42", "django50"],
            ]
            package = "skip"
            deps = ["pytest"]
            commands = [["python", "-c", "print('ok')"]]

            [env.django-py314-django50]
            description = "bleeding edge"
        """),
    })
    outcome = project.run("c", "-e", "django-py314-django50", "-k", "description")
    outcome.assert_success()
    outcome.assert_out_err("[testenv:django-py314-django50]\ndescription = bleeding edge\n", "")


def test_env_base_doc_reference_generative_section_names(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.py311-venv]
            factors = [["x86", "x64"]]
            package = "skip"
            base_python = {replace = "if", condition = "factor.x86", then = "python3.11-32", else = "python3.11-64"}
            env_dir = {replace = "if", condition = "factor.x86", then = ".venv-x86", else = ".venv-x64"}
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    assert "py311-venv-x86" in result.out
    assert "py311-venv-x64" in result.out


def test_env_base_cartesian_with_range(tox_project: ToxProjectCreator) -> None:
    project = tox_project({
        "tox.toml": textwrap.dedent("""\
            [env_base.django]
            factors = [["a", "b"], {"prefix" = "py3", "start" = 12, "stop" = 13}]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = project.run("l")
    result.assert_success()
    for env in ("django-a-py312", "django-a-py313", "django-b-py312", "django-b-py313"):
        assert env in result.out
