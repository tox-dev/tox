from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING, Callable, List

import pytest

from tox.config.loader.ini import IniLoader
from tox.config.loader.ini.factor import filter_for_env, find_envs
from tox.config.source.ini_section import IniSection

if TYPE_CHECKING:
    from configparser import ConfigParser

    from tests.conftest import ToxIniCreator
    from tox.config.main import Config


def test_factor_env_discover_empty() -> None:
    result = list(find_envs("\n\n"))
    assert result == []


@pytest.fixture(scope="session")
def complex_example() -> str:
    return dedent(
        """
    default
    lines
    py: py only
    !py: not py
    {py,!pi}-{a,b}{,-dev},c: complex
    py, d: space
    extra: extra
    more-default
    no:space
    trailingcolon:
    tab:\ttab
    """,
    )


def test_factor_env_discover(complex_example: str) -> None:
    result = list(find_envs(complex_example))
    assert result == [
        "py",
        "py-a",
        "py-a-dev",
        "py-b",
        "py-b-dev",
        "pi-a",
        "pi-a-dev",
        "pi-b",
        "pi-b-dev",
        "c",
        "d",
        "extra",
        "trailingcolon",
        "tab",
    ]


@pytest.mark.parametrize(
    "env",
    [
        "py",
        "py-a",
        "py-a-dev",
        "py-b",
        "py-b-dev",
        "pi-a",
        "pi-a-dev",
        "pi-b",
        "pi-b-dev",
        "c",
        "extra",
        "trailingcolon",
        "tab",
    ],
)
def test_factor_env_filter(env: str, complex_example: str) -> None:
    result = filter_for_env(complex_example, name=env)
    assert "default" in result
    assert "lines" in result
    assert "more-default" in result
    assert "no:space" in result
    if "py" in env:
        assert "py only" in result
        assert "not py" not in result
    else:
        assert "py only" not in result
        assert "not py" in result
    if env == "extra":
        assert "extra" in result
    else:
        assert "extra" not in result
    if env in {"py-a", "py-a-dev", "py-b", "py-b-dev", "c"}:
        assert "complex" in result
    else:
        assert "complex" not in result


def test_factor_env_list(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf("[tox]\nenv_list = {py27,py36}-django{ 15, 16 }{,-dev}, docs, flake")
    result = list(config)
    assert result == [
        "py27-django15",
        "py27-django15-dev",
        "py27-django16",
        "py27-django16-dev",
        "py36-django15",
        "py36-django15-dev",
        "py36-django16",
        "py36-django16-dev",
        "docs",
        "flake",
    ]


def test_simple_env_list(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf("[tox]\nenv_list = docs, flake8")
    assert list(config) == ["docs", "flake8"]


def test_factor_config(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf(
        """
        [tox]
        env_list = {py36,py37}-{django15,django16}
        [testenv]
        deps-x =
            pytest
            django15: Django>=1.5,<1.6
            django16: Django>=1.6,<1.7
            py36: unittest2
            !py37,!django16: negation-or
            !py37-!django16: negation-and
        """,
    )
    assert list(config) == ["py36-django15", "py36-django16", "py37-django15", "py37-django16"]
    for env in config.core["env_list"]:
        env_config = config.get_env(env)
        env_config.add_config(keys="deps-x", of_type=List[str], default=[], desc="deps")
        deps = env_config["deps-x"]
        assert "pytest" in deps
        if "py36" in env:
            assert "unittest2" in deps
            assert "negation-or" in deps
        if "django15" in env:
            assert "Django>=1.5,<1.6" in deps
            assert "negation-or" in deps
        if "django16" in env:
            assert "Django>=1.6,<1.7" in deps
        if env_config.name == "py36-django15":
            assert "negation-and" in deps


def test_factor_config_do_not_replace_unescaped_comma(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf("[tox]\nenv_list = py37-{base,i18n},b")
    assert list(config) == ["py37-base", "py37-i18n", "b"]


def test_factor_config_no_env_list_creates_env(tox_ini_conf: ToxIniCreator) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    config = tox_ini_conf(
        """
        [tox]
        env_list = py37-{django15,django16}
        [testenv]
        deps =
            pytest
            django15: Django>=1.5,<1.6
            django16: Django>=1.6,<1.7
            py36: unittest2
        """,
    )

    assert list(config) == ["py37-django15", "py37-django16", "py36"]


@pytest.mark.parametrize(
    ("env_list", "expected_envs"),
    [
        pytest.param("py3{10-13}", ["py310", "py311", "py312", "py313"], id="Expand positive range"),
        pytest.param("py3{10-11},a", ["py310", "py311", "a"], id="Expand range and add additional env"),
        pytest.param("py3{10-11},a{1-2}", ["py310", "py311", "a1", "a2"], id="Expand multiple env with ranges"),
        pytest.param(
            "py3{10-12,14}",
            ["py310", "py311", "py312", "py314"],
            id="Expand ranges, and allow extra parameter in generator",
        ),
        pytest.param(
            "py3{8-10,12,14-16}",
            ["py38", "py39", "py310", "py312", "py314", "py315", "py316"],
            id="Expand multiple ranges for one generator",
        ),
        pytest.param(
            "py3{10-11}-django1.{3-5}",
            [
                "py310-django1.3",
                "py310-django1.4",
                "py310-django1.5",
                "py311-django1.3",
                "py311-django1.4",
                "py311-django1.5",
            ],
            id="Expand ranges and factor multiple environment parts",
        ),
        pytest.param(
            "py3{10-11, 13}-django1.{3-4, 6}",
            [
                "py310-django1.3",
                "py310-django1.4",
                "py310-django1.6",
                "py311-django1.3",
                "py311-django1.4",
                "py311-django1.6",
                "py313-django1.3",
                "py313-django1.4",
                "py313-django1.6",
            ],
            id="Expand ranges and parameters and factor multiple environment parts",
        ),
        pytest.param(
            "py3{10-11},a{1-2}-b{3-4}",
            ["py310", "py311", "a1-b3", "a1-b4", "a2-b3", "a2-b4"],
            id="Expand ranges and parameters & factor multiple environment parts for multiple generative environments",
        ),
        pytest.param("py3{13-11}", ["py313", "py312", "py311"], id="Expand negative ranges"),
        pytest.param("3.{10-13}", ["3.10", "3.11", "3.12", "3.13"], id="Expand new-style python envs"),
        pytest.param("py3{-11}", ["py3-11"], id="Don't expand left-open numerical range"),
        pytest.param("foo{11-}", ["foo11-"], id="Don't expand right-open numerical range"),
        pytest.param("foo{a-}", ["fooa-"], id="Don't expand right-open range"),
        pytest.param("foo{-a}", ["foo-a"], id="Don't expand left-open range"),
        pytest.param("foo{a-11}", ["fooa-11"], id="Don't expand alpha-umerical range"),
        pytest.param("foo{13-a}", ["foo13-a"], id="Don't expand numerical-alpha range"),
        pytest.param("foo{a-b}", ["fooa-b"], id="Don't expand non-numerical range"),
    ],
)
def test_env_list_expands_ranges(env_list: str, expected_envs: list[str], tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf(
        f"""
        [tox]
        env_list = {env_list}
        """
    )

    assert list(config) == expected_envs


@pytest.mark.parametrize(
    ("env", "result"),
    [
        ("py35", "python -m coverage html -d cov"),
        ("py36", "python -m coverage html -d cov\n--show-contexts"),
    ],
)
def test_ini_loader_raw_with_factors(
    mk_ini_conf: Callable[[str], ConfigParser],
    env: str,
    result: str,
    empty_config: Config,
) -> None:
    commands = "python -m coverage html -d cov \n    !py35: --show-contexts"
    loader = IniLoader(
        section=IniSection(None, "testenv"),
        parser=mk_ini_conf(f"[tox]\nenvlist=py35,py36\n[testenv]\ncommands={commands}"),
        overrides=[],
        core_section=IniSection(None, "tox"),
    )
    outcome = loader.load_raw(key="commands", conf=empty_config, env_name=env)
    assert outcome == result


def test_generative_section_name_with_ranges(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf(
        """
        [testenv:py3{11-13}-{black,lint}]
        deps-x =
            black: black
            lint: flake8
        """,
    )
    assert list(config) == ["py311-black", "py311-lint", "py312-black", "py312-lint", "py313-black", "py313-lint"]


def test_generative_section_name(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf(
        """
        [testenv:{py311,py310}-{black,lint}]
        deps-x =
            black: black
            lint: flake8
        """,
    )
    assert list(config) == ["py311-black", "py311-lint", "py310-black", "py310-lint"]

    env_config = config.get_env("py311-black")
    env_config.add_config(keys="deps-x", of_type=List[str], default=[], desc="deps")
    deps = env_config["deps-x"]
    assert deps == ["black"]

    env_config = config.get_env("py311-lint")
    env_config.add_config(keys="deps-x", of_type=List[str], default=[], desc="deps")
    deps = env_config["deps-x"]
    assert deps == ["flake8"]


def test_multiple_factor_match(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf("[testenv]\nconf = a{,-b}: x")
    env_config = config.get_env("a-b")
    env_config.add_config(keys="conf", of_type=str, default="", desc="conf")
    deps = env_config["conf"]
    assert deps == "x"
