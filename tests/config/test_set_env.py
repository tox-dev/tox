from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, Literal
from unittest.mock import ANY

import pytest

from tox.config.set_env import SetEnv

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tox.config.set_env import SetEnvRaw
    from tox.pytest import MonkeyPatch, ToxProjectCreator

from typing import Protocol


def test_set_env_explicit() -> None:
    set_env = SetEnv("\nA=1\nB = 2\nC= 3\nD= 4", "py", "py", Path())
    set_env.update({"E": "5 ", "F": "6"}, override=False)

    keys = list(set_env)
    assert keys == ["E", "F", "A", "B", "C", "D"]
    values = [set_env.load(k) for k in keys]
    assert values == ["5 ", "6", "1", "2", "3", "4"]

    for key in keys:
        assert key in set_env
    assert "MISS" not in set_env


def test_set_env_merge() -> None:
    a = SetEnv("\nA=1\nB = 2\nC= 3\nD= 4", "py", "py", Path())
    b = SetEnv("\nA=2\nE = 5", "py", "py", Path())
    a.update(b, override=False)

    keys = list(a)
    assert keys == ["E", "A", "B", "C", "D"]
    values = [a.load(k) for k in keys]
    assert values == ["5", "1", "2", "3", "4"]

    a.update(b, override=True)

    values = [a.load(k) for k in keys]
    assert values == ["5", "2", "2", "3", "4"]


def test_set_env_bad_line() -> None:
    with pytest.raises(ValueError, match="A"):
        SetEnv("A", "py", "py", Path())


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        pytest.param([], {}, id="empty"),
        pytest.param([{}], {}, id="empty-entry"),
        pytest.param([{}, {"A": "1"}, {}, {"A": "2", "B": "3"}], {"A": "2", "B": "3"}, id="later-wins"),
    ],
)
def test_set_env_list(raw: SetEnvRaw, expected: dict[str, str]) -> None:
    set_env = SetEnv(raw, "py", "py", Path())
    assert {key: set_env.load(key) for key in set_env} == expected


@pytest.mark.parametrize("empty", [pytest.param("[]", id="list"), pytest.param("{}", id="table")])
def test_set_env_empty_override(tox_project: ToxProjectCreator, empty: str) -> None:
    project = tox_project({
        "tox.toml": f"""
        [env_run_base]
        set_env = {{ INHERITED = "value" }}
        [env.py]
        set_env = {empty}
        """
    })
    outcome = project.run("c", "-e", "py", "-k", "set_env", "--hashseed", "1")
    outcome.assert_success()
    work_dir = project.path / ".tox"
    outcome.assert_out_err(
        "[testenv:py]\nset_env =\n  PIP_DISABLE_PIP_VERSION_CHECK=1\n  PIP_USER=0\n  PYTHONHASHSEED=1\n"
        f"  PYTHONIOENCODING=utf-8\n  TOX_ENV_DIR={work_dir / 'py'}\n  TOX_ENV_NAME=py\n  TOX_WORK_DIR={work_dir}\n"
        f"  VIRTUAL_ENV={work_dir / 'py'}\n",
        "",
    )


ConfigFileFormat = Literal["ini", "toml"]


class EvalSetEnv(Protocol):
    def __call__(
        self,
        config: str,
        *,
        of_type: ConfigFileFormat = "ini",
        extra_files: dict[str, Any] | None = ...,
        from_cwd: Path | None = ...,
    ) -> SetEnv: ...


@pytest.fixture
def eval_set_env(tox_project: ToxProjectCreator) -> EvalSetEnv:
    def func(
        config: str,
        *,
        of_type: ConfigFileFormat = "ini",
        extra_files: dict[str, Any] | None = None,
        from_cwd: Path | None = None,
    ) -> SetEnv:
        prj = tox_project({f"tox.{of_type}": config, **(extra_files or {})})
        result = prj.run("c", "-k", "set_env", "-e", "py", from_cwd=None if from_cwd is None else prj.path / from_cwd)
        result.assert_success()
        return result.env_conf("py").get("set_env", SetEnv)

    return func


_EXPORTED: Final = {"PIP_USER": "0", "TOX_ENV_DIR": ANY, "TOX_ENV_NAME": "py", "TOX_WORK_DIR": ANY, "VIRTUAL_ENV": ANY}


def test_set_env_default(eval_set_env: EvalSetEnv) -> None:
    set_env = eval_set_env("")
    assert {key: set_env.load(key) for key in set_env} == {
        "PYTHONHASHSEED": ANY,
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONIOENCODING": "utf-8",
        **_EXPORTED,
    }


def test_set_env_self_key(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("a", "1")
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=a={env:a:2}")
    assert set_env.load("a") == "1"


def test_set_env_other_env_set(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("b", "1")
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=a={env:b:2}")
    assert set_env.load("a") == "1"


def test_set_env_other_env_default(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("b", raising=False)
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=a={env:b:2}")
    assert set_env.load("a") == "2"


def test_set_env_delayed_eval(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("b", "c=1")
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env={env:b}")
    assert set_env.load("c") == "1"


def test_set_env_tty_on(eval_set_env: EvalSetEnv, mocker: MockerFixture) -> None:
    mocker.patch("sys.stdout.isatty", return_value=True)
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env={tty:A=1:B=1}")
    assert set_env.load("A") == "1"
    assert "B" not in set_env


def test_set_env_tty_off(eval_set_env: EvalSetEnv, mocker: MockerFixture) -> None:
    mocker.patch("sys.stdout.isatty", return_value=False)
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env={tty:A=1:B=1}")
    assert set_env.load("B") == "1"
    assert "A" not in set_env


def test_set_env_circular_use_os_environ(tox_project: ToxProjectCreator) -> None:
    prj = tox_project({"tox.ini": "[testenv]\npackage=skip\nset_env=a={env:b}\n b={env:a}"})
    result = prj.run("c", "-e", "py", raise_on_config_fail=False)
    result.assert_failed(code=-1)
    assert "replace failed in py.set_env with MatchRecursionError" in result.out, result.out
    assert "circular chain between set env a, b" in result.out, result.out


def test_set_env_invalid_lines(eval_set_env: EvalSetEnv) -> None:
    with pytest.raises(ValueError, match="a"):
        eval_set_env("[testenv]\npackage=skip\nset_env=a\n b")


def test_set_env_replacer(eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("MAGIC", "\nb=2\n")
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=a=1\n {env:MAGIC}")
    env = {k: set_env.load(k) for k in set_env}
    assert env == {
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "a": "1",
        "b": "2",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONHASHSEED": ANY,
        **_EXPORTED,
    }


def test_set_env_honor_override(eval_set_env: EvalSetEnv) -> None:
    set_env = eval_set_env("[testenv]\npackage=skip\nset_env=PIP_DISABLE_PIP_VERSION_CHECK=0")
    assert set_env.load("PIP_DISABLE_PIP_VERSION_CHECK") == "0"


@pytest.mark.parametrize(
    ("of_type", "config"),
    [
        pytest.param("ini", "[testenv]\npackage=skip\nset_env=file|A{/}a.txt\nchange_dir=C", id="ini"),
        pytest.param("toml", '[env_run_base]\npackage="skip"\nset_env={file="A{/}a.txt"}\nchange_dir="C"', id="toml"),
        pytest.param("ini", "[testenv]\npackage=skip\nset_env=file|{env:env_file}\nchange_dir=C", id="ini-env"),
        pytest.param(
            "toml", '[env_run_base]\npackage="skip"\nset_env={file="{env:env_file}"}\nchange_dir="C"', id="toml-env"
        ),
    ],
)
def test_set_env_environment_file(
    of_type: ConfigFileFormat, config: str, eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch
) -> None:
    env_file = """
    A=1
    B= 2
    C = 1
    # D = comment # noqa: E800
    E = "1"
    F =
    """
    monkeypatch.setenv("env_file", "A{/}a.txt")

    extra = {"A": {"a.txt": env_file}, "B": None, "C": None}
    set_env = eval_set_env(config, of_type=of_type, extra_files=extra, from_cwd=Path("B"))
    content = {k: set_env.load(k) for k in set_env}
    assert content == {
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONHASHSEED": ANY,
        "A": "1",
        "B": "2",
        "C": "1",
        "E": '"1"',
        "F": "",
        "PYTHONIOENCODING": "utf-8",
        **_EXPORTED,
    }


def test_set_env_environment_file_is_utf8(eval_set_env: EvalSetEnv) -> None:
    set_env = eval_set_env(
        "[testenv]\npackage=skip\nset_env=file|.env",
        extra_files={".env": "GREETING=Grüße\n"},
    )
    assert set_env.load("GREETING") == "Grüße"


@pytest.mark.parametrize(
    ("of_type", "config"),
    [
        pytest.param("ini", "[testenv]\npackage=skip\nset_env=file|A{/}a.txt\n X=y\nchange_dir=C", id="ini"),
        pytest.param(
            "toml", '[env_run_base]\npackage="skip"\nset_env={file="A{/}a.txt", X="y"}\nchange_dir="C"', id="toml"
        ),
        pytest.param("ini", "[testenv]\npackage=skip\nset_env=file|{env:env_file}\n X=y\nchange_dir=C", id="ini-env"),
        pytest.param(
            "toml",
            '[env_run_base]\npackage="skip"\nset_env={file="{env:env_file}", X="y"}\nchange_dir="C"',
            id="toml-env",
        ),
    ],
)
def test_set_env_environment_file_combined_with_normal_setting(
    of_type: ConfigFileFormat, config: str, eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch
) -> None:
    env_file = """
    A=1
    """
    # Monkeypatch only used for some of the parameters
    monkeypatch.setenv("env_file", "A{/}a.txt")

    extra = {"A": {"a.txt": env_file}, "B": None, "C": None}
    set_env = eval_set_env(config, of_type=of_type, extra_files=extra, from_cwd=Path("B"))
    content = {k: set_env.load(k) for k in set_env}
    assert content == {
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONHASHSEED": ANY,
        "A": "1",
        "X": "y",
        "PYTHONIOENCODING": "utf-8",
        **_EXPORTED,
    }


def test_set_env_file_keeps_semicolon_in_value(tox_project: ToxProjectCreator) -> None:
    ini = """\
    [testenv]
    skip_install = true
    set_env =
        file|.env
    """
    env_file = "DATABASE_URL=postgresql://host/db?opt=1;sslmode=require\nFLAGS=a;b\n"
    project = tox_project({"tox.ini": ini, ".env": env_file})
    result = project.run("c", "-e", "py", "-k", "set_env")
    result.assert_success()
    set_env = result.env_conf("py")["set_env"]
    content = {k: set_env.load(k) for k in set_env}
    assert content["DATABASE_URL"] == "postgresql://host/db?opt=1;sslmode=require"
    assert content["FLAGS"] == "a;b"


def test_set_env_file_does_not_override_later_values(tox_project: ToxProjectCreator) -> None:
    ini = """\
    [testenv]
    skip_install = true
    set_env =
        file|.env
        FOO=QUX
    """
    project = tox_project({"tox.ini": ini, ".env": "FOO=BAR\nEXTRA=from_file"})
    result = project.run("c", "-e", "py", "-k", "set_env")
    result.assert_success()
    set_env = result.env_conf("py")["set_env"]
    content = {k: set_env.load(k) for k in set_env}
    assert content["FOO"] == "QUX"
    assert content["EXTRA"] == "from_file"


def test_set_env_list_keeps_every_file_entry(tox_project: ToxProjectCreator) -> None:
    toml = """\
    [env_run_base]
    skip_install = true
    set_env = [{ file = "a.env" }, { file = "b.env" }]
    """
    project = tox_project({"tox.toml": toml, "a.env": "A=1", "b.env": "B=2"})
    result = project.run("c", "-e", "py", "-k", "set_env")
    result.assert_success()
    set_env = result.env_conf("py")["set_env"]
    content = {k: set_env.load(k) for k in set_env}
    assert content["A"] == "1"
    assert content["B"] == "2"


def test_set_env_list_file_does_not_override_later_values(tox_project: ToxProjectCreator) -> None:
    toml = """\
    [env_run_base]
    skip_install = true
    set_env = [{ FOO = "BAR" }, { file = ".env" }, { FOO = "QUX" }]
    """
    project = tox_project({"tox.toml": toml, ".env": "FOO=from_file\nEXTRA=from_file"})
    result = project.run("c", "-e", "py", "-k", "set_env")
    result.assert_success()
    set_env = result.env_conf("py")["set_env"]
    content = {k: set_env.load(k) for k in set_env}
    assert content["FOO"] == "QUX"
    assert content["EXTRA"] == "from_file"


def test_set_env_environment_file_missing(tox_project: ToxProjectCreator) -> None:
    project = tox_project({"tox.ini": "[testenv]\npackage=skip\nset_env=file|magic.txt"})
    result = project.run("r")
    result.assert_failed()
    assert f"py: failed with {project.path / 'magic.txt'} does not exist for set_env" in result.out


# https://github.com/tox-dev/tox/issues/2435
def test_set_env_environment_with_file_and_expanded_substitution(
    tox_project: ToxProjectCreator, monkeypatch: MonkeyPatch
) -> None:
    conf = {
        "tox.ini": """
        [tox]
        envlist =
            check

        [testenv]
        setenv =
            file|.env
            PRECENDENCE_TEST_1=1_expanded_precedence

        [testenv:check]
        setenv =
            {[testenv]setenv}
            PRECENDENCE_TEST_1=1_self_precedence
            PRECENDENCE_TEST_2=2_self_precedence
        """,
        ".env": """
        PRECENDENCE_TEST_1=1_file_precedence
        PRECENDENCE_TEST_2=2_file_precedence
        PRECENDENCE_TEST_3=3_file_precedence
        """,
    }
    monkeypatch.setenv("env_file", ".env")
    project = tox_project(conf)

    result = project.run("c", "-k", "set_env", "-e", "check")
    result.assert_success()
    set_env = result.env_conf("check")["set_env"]
    content = {k: set_env.load(k) for k in set_env}
    assert content == {
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PYTHONHASHSEED": ANY,
        "PYTHONIOENCODING": "utf-8",
        "PRECENDENCE_TEST_1": "1_self_precedence",
        "PRECENDENCE_TEST_2": "2_self_precedence",
        "PRECENDENCE_TEST_3": "3_file_precedence",
        **_EXPORTED,
        "TOX_ENV_NAME": "check",
    }

    result = project.run("r", "-e", "check")
    result.assert_success()
    assert "check: OK" in result.out


@pytest.mark.parametrize(
    ("of_type", "config", "expected_present", "expected_value"),
    [
        pytest.param(
            "ini",
            f"[testenv]\npackage=skip\nset_env=CONDITIONAL=value; sys_platform == '{sys.platform}'",
            True,
            "value",
            id="ini-marker-true",
        ),
        pytest.param(
            "ini",
            "[testenv]\npackage=skip\nset_env=CONDITIONAL=value; sys_platform == 'nonexistent'",
            False,
            None,
            id="ini-marker-false",
        ),
        pytest.param(
            "ini",
            f"[testenv]\npackage=skip\nset_env=CONDITIONAL=can't; sys_platform == '{sys.platform}'",
            True,
            "can't",
            id="ini-marker-true-apostrophe-value",
        ),
        pytest.param(
            "ini",
            "[testenv]\npackage=skip\nset_env=CONDITIONAL=can't; sys_platform == 'nonexistent'",
            False,
            None,
            id="ini-marker-false-apostrophe-value",
        ),
        pytest.param(
            "toml",
            f'[env_run_base]\npackage="skip"\nset_env.CONDITIONAL = {{ value = "value", '
            f"marker = \"sys_platform == '{sys.platform}'\" }}",
            True,
            "value",
            id="toml-marker-true",
        ),
        pytest.param(
            "toml",
            '[env_run_base]\npackage="skip"\n'
            'set_env.CONDITIONAL = { value = "value", marker = "sys_platform == \'nonexistent\'" }',
            False,
            None,
            id="toml-marker-false",
        ),
        pytest.param(
            "ini",
            "[testenv]\npackage=skip\nset_env=UNCONDITIONAL=value",
            True,
            "value",
            id="ini-no-marker",
        ),
        pytest.param(
            "ini",
            f"[testenv]\npackage=skip\nset_env=OS_CHECK=yes; os_name == '{os.name}'",
            True,
            "yes",
            id="ini-os-name-marker",
        ),
    ],
)
def test_set_env_marker(
    eval_set_env: EvalSetEnv,
    of_type: ConfigFileFormat,
    config: str,
    expected_present: bool,
    expected_value: str | None,
) -> None:
    set_env = eval_set_env(config, of_type=of_type)
    if expected_present:
        assert "CONDITIONAL" in set_env or "UNCONDITIONAL" in set_env or "OS_CHECK" in set_env
        key = next(k for k in ("CONDITIONAL", "UNCONDITIONAL", "OS_CHECK") if k in set_env)
        assert set_env.load(key) == expected_value
    else:
        assert "CONDITIONAL" not in set_env


@pytest.mark.parametrize(
    ("marker", "expected_present"),
    [
        pytest.param(f"sys_platform == '{sys.platform}'", True, id="marker-true"),
        pytest.param("sys_platform == 'nonexistent'", False, id="marker-false"),
    ],
)
def test_set_env_marker_with_replace_toml(
    eval_set_env: EvalSetEnv, monkeypatch: MonkeyPatch, marker: str, expected_present: bool
) -> None:
    monkeypatch.setenv("MY_VAR", "from_env")
    config = (
        f'[env_run_base]\npackage="skip"\n'
        f'set_env.CONDITIONAL = {{ replace = "env", name = "MY_VAR", default = "default", marker = "{marker}" }}'
    )
    set_env = eval_set_env(config, of_type="toml")
    if expected_present:
        assert "CONDITIONAL" in set_env
        assert set_env.load("CONDITIONAL") == "from_env"
    else:
        assert "CONDITIONAL" not in set_env


@pytest.mark.parametrize(
    ("ini", "env", "expected"),
    [
        pytest.param(
            """\
            [testenv]
            skip_install = true
            set_env =
                OS_TEST_PATH=./tests/unit
            commands = python -c "import os; print(os.environ['OS_TEST_PATH'])"

            [testenv:functional]
            set_env =
              {[testenv]set_env}
              OS_TEST_PATH=./tests/functional
            commands = python -c "import os; print(os.environ['OS_TEST_PATH'])"

            [testenv:functional-py]
            set_env = {[testenv:functional]set_env}
            commands = {[testenv:functional]commands}
            """,
            "functional-py",
            "./tests/functional",
            id="via-referenced-section",
        ),
        pytest.param(
            """\
            [testenv]
            skip_install = true
            set_env =
                COVERAGE_FILE=THISISBAD

            [testenv:coverage_report]
            set_env =
                {[testenv]set_env}
                COVERAGE_FILE=THISISGOOD
            commands = python -c "import os; print(os.environ['COVERAGE_FILE'])"
            """,
            "coverage_report",
            "THISISGOOD",
            id="direct",
        ),
    ],
)
def test_set_env_cross_section_override(tox_project: ToxProjectCreator, ini: str, env: str, expected: str) -> None:
    result = tox_project({"tox.ini": textwrap.dedent(ini)}).run("r", "-e", env)
    result.assert_success()
    assert result.out.splitlines()[1] == expected


def test_set_env_escaped_semicolon() -> None:
    set_env = SetEnv(r"FOO=a\;b", "py", "py", Path())
    assert set_env.load("FOO") == "a;b"


@pytest.mark.parametrize(
    ("of_type", "config"),
    [
        pytest.param(
            "ini",
            "[testenv]\npackage=skip\nset_env=FOO=conditional; sys_platform == 'nonexistent'\n FOO=unconditional",
            id="inline",
        ),
        pytest.param(
            "ini",
            "[testenv]\npackage=skip\nset_env=FOO=conditional; sys_platform == 'nonexistent'\n file|.env",
            id="ini-file",
        ),
        pytest.param(
            "toml",
            '[env_run_base]\npackage="skip"\n'
            'set_env = {FOO={value="conditional", marker="sys_platform == \'nonexistent\'"}, file=".env"}',
            id="toml-file",
        ),
    ],
)
def test_set_env_unconditional_override(eval_set_env: EvalSetEnv, of_type: ConfigFileFormat, config: str) -> None:
    set_env = eval_set_env(config, of_type=of_type, extra_files={".env": "FOO=unconditional\n"})
    assert "FOO" in set_env
    assert set_env.load("FOO") == "unconditional"


def test_set_env_marker_mixed(eval_set_env: EvalSetEnv) -> None:
    marker = f"sys_platform == '{sys.platform}'"
    config = (
        f"[testenv]\npackage=skip\nset_env=ALWAYS=1\n CONDITIONAL=2; {marker}\n NEVER=3; sys_platform == 'nonexistent'"
    )
    set_env = eval_set_env(config)
    keys = list(set_env)
    assert "ALWAYS" in keys
    assert "CONDITIONAL" in keys
    assert "NEVER" not in keys


def test_set_env_list_unconditional_entry_drops_earlier_marker(eval_set_env: EvalSetEnv) -> None:
    config = (
        "[env_run_base]\npackage='skip'\n"
        'set_env = [{ FOO = { value = "conditional", marker = "sys_platform == \'nonexistent\'" } },'
        ' { FOO = "always" }]'
    )
    set_env = eval_set_env(config, of_type="toml")
    assert "FOO" in set_env
    assert set_env.load("FOO") == "always"


def test_set_env_list_keeps_marker_of_last_entry(eval_set_env: EvalSetEnv) -> None:
    config = (
        "[env_run_base]\npackage='skip'\n"
        'set_env = [{ FOO = "always" },'
        ' { FOO = { value = "conditional", marker = "sys_platform == \'nonexistent\'" } }]'
    )
    set_env = eval_set_env(config, of_type="toml")
    assert "FOO" not in set_env


@pytest.mark.parametrize(
    ("base", "child", "expected"),
    [
        pytest.param(
            ["FOO = base; sys_platform == 'nonexistent'"],
            ["{[testenv:base]set_env}", "FOO = own"],
            "own",
            id="own-line-wins-over-spliced-marker",
        ),
        pytest.param(
            ["FOO = base; sys_platform == 'nonexistent'", "FOO = redefined"],
            ["{[testenv:base]set_env}"],
            "redefined",
            id="spliced-redefinition-drops-marker",
        ),
        pytest.param(
            ["FOO = base; sys_platform == 'nonexistent'", "file|.env"],
            ["{[testenv:base]set_env}"],
            "from-file",
            id="spliced-file-drops-marker",
        ),
        pytest.param(
            ["FOO = base; sys_platform == 'nonexistent'"],
            ["{[testenv:base]set_env}"],
            "None",
            id="spliced-marker-gates-its-value",
        ),
    ],
)
def test_set_env_spliced_marker(
    tox_project: ToxProjectCreator, base: list[str], child: list[str], expected: str
) -> None:
    ini = "\n".join([
        "[testenv]",
        "package = skip",
        """commands = python -c "import os; print(os.environ.get('FOO'))\"""",
        "[testenv:base]",
        "set_env =",
        *(f"    {line}" for line in base),
        "[testenv:child]",
        "set_env =",
        *(f"    {line}" for line in child),
    ])
    result = tox_project({"tox.ini": ini, ".env": "FOO=from-file\n"}).run("r", "-e", "child")

    result.assert_success()
    assert result.out.splitlines()[1] == expected


@pytest.mark.parametrize(
    ("of_type", "config", "environ", "expected"),
    [
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                BASE = /opt/app
                DATA = {env:BASE}/data
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            {},
            {"DATA": "/opt/app/data"},
            id="ini-sibling-key",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                BASE = /b
                VALUE = {posargs:{env:BASE}}
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            {},
            {"VALUE": "/b"},
            id="ini-posargs-default",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                BASE = /a
                {env:LINES}
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            {"LINES": "FROM_LINES = {env:BASE}/lines"},
            {"FROM_LINES": "/a/lines"},
            id="ini-env-lines-see-block",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                {env:KNAME} = 1
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            {"KNAME": "FOO"},
            {"FOO": "1"},
            id="ini-key-substitution",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                A = fromblock
                file|a.env
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            {},
            {"A": "fromblock", "FROM_FILE": "fromblock-x"},
            id="ini-file",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                FOO = a
                {[b]set_env}
            [b]
            set_env =
                FOO = b
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            {},
            {"FOO": "a"},
            id="ini-nested-direct-beats-include",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                {[b]set_env}
                FOO = a
            [b]
            set_env =
                FOO = b
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            {},
            {"FOO": "a"},
            id="ini-nested-include-then-direct",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                FOO = a
            [b]
            set_env =
                FOO = b
            [testenv]
            package = skip
            set_env =
                {[a]set_env}
                {[b]set_env}
            """,
            {},
            {"FOO": "b"},
            id="ini-later-include-wins",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                {[c]set_env}
            [b]
            set_env =
                FOO = b
            [c]
            set_env =
                FOO = c
            [testenv]
            package = skip
            set_env =
                {[a]set_env}
                {[b]set_env}
            """,
            {},
            {"FOO": "b"},
            id="ini-later-include-wins-over-deeper",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                FOO = a
                BASE = /a
                DATA = {env:BASE}/data
            [testenv]
            package = skip
            set_env =
                FOO = own
                BASE = /own
                {[a]set_env}
            """,
            {},
            {"FOO": "own", "DATA": "/own/data"},
            id="ini-own-key-wins",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                {[c]set_env}
                A = a
            [b]
            set_env =
                {[c]set_env}
                B = b
            [c]
            set_env =
                C = c
            [testenv]
            package = skip
            set_env =
                {[a]set_env}
                {[b]set_env}
            """,
            {},
            {"A": "a", "B": "b", "C": "c"},
            id="ini-diamond",
        ),
        pytest.param(
            "ini",
            """
            [base]
            root = /r
            [a]
            set_env =
                PATH_VALUE = {[base]root}/x
                HASH = a\\#b
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            {},
            {"PATH_VALUE": "/r/x", "HASH": "a#b"},
            id="ini-section-reference-and-escaped-hash",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                HIDDEN = 1; sys_platform == "nonexistent"
                SHOWN = 2
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            {},
            {"HIDDEN": None, "SHOWN": "2"},
            id="ini-marker",
        ),
        pytest.param(
            "toml",
            """
            [env_run_base]
            package = "skip"
            set_env = { BASE = "/opt/app", DATA = { replace = "env", name = "BASE" } }
            """,
            {"BASE": "/host"},
            {"DATA": "/opt/app"},
            id="toml-env-table-sibling-key",
        ),
        pytest.param(
            "toml",
            f"""
            [env_run_base]
            package = "skip"
            set_env.BASE = "/opt/app"
            set_env.DATA = {{ replace = "env", name = "BASE", marker = "sys_platform == '{sys.platform}'" }}
            set_env.HIDDEN = {{ replace = "env", name = "BASE", marker = "sys_platform == 'nonexistent'" }}
            """,
            {"BASE": "/host"},
            {"DATA": "/opt/app", "HIDDEN": None},
            id="toml-env-table-marker",
        ),
        pytest.param(
            "toml",
            """
            [env.a]
            set_env = { BASE = "/opt/app", DATA = { replace = "env", name = "BASE" } }
            [env_run_base]
            package = "skip"
            set_env = { replace = "ref", of = ["env", "a", "set_env"] }
            """,
            {"BASE": "/host"},
            {"DATA": "/opt/app"},
            id="toml-env-table-in-ref",
        ),
        pytest.param(
            "toml",
            """
            [env_run_base]
            package = "skip"
            set_env = { BASE = "/opt/app", DATA = { replace = "env", name = "MISSING", default = "{env:BASE}/d" } }
            """,
            {"BASE": "/host"},
            {"DATA": "/opt/app/d"},
            id="toml-env-table-default",
        ),
        pytest.param(
            "toml",
            """
            [env_run_base]
            package = "skip"
            set_env = { DATA = { replace = "env", name = "MISSING", default = "a}b{c" } }
            """,
            {},
            {"DATA": "a}b{c"},
            id="toml-env-table-default-unpaired-braces",
        ),
    ],
)
def test_set_env_include_resolves_values_when_read(
    eval_set_env: EvalSetEnv,
    monkeypatch: MonkeyPatch,
    of_type: ConfigFileFormat,
    config: str,
    environ: dict[str, str],
    expected: dict[str, str | None],
) -> None:
    for key, value in environ.items():
        monkeypatch.setenv(key, value)
    set_env = eval_set_env(textwrap.dedent(config), of_type=of_type, extra_files={"a.env": "FROM_FILE={env:A}-x\n"})
    assert {key: set_env.load(key) if key in set_env else None for key in expected} == expected


@pytest.mark.parametrize(
    ("of_type", "config", "message"),
    [
        pytest.param(
            "ini",
            """
            [a]
            set_env = {[b]set_env}
            [b]
            set_env = {[a]set_env}
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            "py: circular set_env reference {[a]set_env} -> {[b]set_env} -> {[a]set_env}",
            id="ini-include-cycle",
        ),
        pytest.param(
            "ini",
            """
            [testenv]
            package = skip
            set_env =
                {[testenv]set_env}
                A = 1
            """,
            "py: circular set_env reference {[testenv]set_env} -> {[testenv]set_env}",
            id="ini-self-include",
        ),
        pytest.param(
            "ini",
            """
            [a]
            set_env =
                A = {env:B}x
                B = {env:A}y
            [testenv]
            package = skip
            set_env = {[a]set_env}
            """,
            "py: replace failed in py.set_env with MatchRecursionError('circular chain between set env A, B')",
            id="ini-included-value-cycle",
        ),
        pytest.param(
            "ini",
            """
            [testenv]
            package = skip
            set_env =
                A = {env:B}x
                B = {env:A}y
            """,
            "py: replace failed in py.set_env with MatchRecursionError('circular chain between set env A, B')",
            id="ini-value-cycle",
        ),
        pytest.param(
            "toml",
            """
            [env_run_base]
            package = "skip"
            set_env = { A = "{env:B}x", B = "{env:A}y" }
            """,
            "py: failed to load py.set_env: circular chain between set env A, B",
            id="toml-value-cycle",
        ),
        pytest.param(
            "toml",
            """
            [env_run_base]
            package = "skip"
            set_env = { replace = "ref", of = ["env_run_base", "set_env"] }
            """,
            "py: failed to load py.set_env: circular reference env_run_base.set_env -> env_run_base.set_env",
            id="toml-self-ref",
        ),
    ],
)
def test_set_env_cycle_fails_env(
    tox_project: ToxProjectCreator, of_type: ConfigFileFormat, config: str, message: str
) -> None:
    result = tox_project({f"tox.{of_type}": textwrap.dedent(config)}).run("r", "-e", "py")

    result.assert_failed(code=1)
    assert f"{message}\n" in result.out


def test_set_env_unresolved_include_line(eval_set_env: EvalSetEnv) -> None:
    with pytest.raises(ValueError, match=r"invalid line '\{\[missing\]set_env\}' in set_env"):
        eval_set_env("[testenv]\npackage=skip\nset_env={[missing]set_env}")


@pytest.mark.parametrize(
    ("line", "key"),
    [
        pytest.param("a-{b: KEY={env:MISSING:value}", "a-{b: KEY", id="unclosed-brace"),
        pytest.param("{unknown} = {env:MISSING:value}", "{unknown}", id="unknown-substitution"),
    ],
)
def test_set_env_unresolved_key_kept_literal(eval_set_env: EvalSetEnv, line: str, key: str) -> None:
    set_env = eval_set_env(f"[testenv]\npackage=skip\nset_env={line}")
    assert set_env.load(key) == "value"


@pytest.mark.parametrize(
    "ini",
    [
        pytest.param("[testenv]\npackage=skip", id="defaults"),
        pytest.param("[testenv]\npackage=skip\nset_env=TOX_ENV_NAME=mine", id="tox-value-wins"),
        pytest.param(
            "[testenv]\npackage=skip\nset_env=FOO={work_dir}{/}custom\nenv_dir={env:FOO}", id="env-dir-from-set-env"
        ),
    ],
)
def test_set_env_shows_what_commands_get(tox_project: ToxProjectCreator, ini: str) -> None:
    result = tox_project({"tox.ini": ini}).run("c", "-e", "py", "-k", "set_env")
    result.assert_success()
    shown, used = result.env_conf("py")["set_env"], result.state.envs["py"].environment_variables
    assert {key: shown.load(key) for key in shown if key in _EXPORTED} == {key: used[key] for key in _EXPORTED}
