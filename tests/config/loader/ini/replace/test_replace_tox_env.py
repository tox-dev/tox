from pathlib import Path
from typing import Callable

import pytest

from tests.config.loader.ini.replace.conftest import ReplaceOne
from tests.conftest import ToxIniCreator
from tox.config.sets import ConfigSet
from tox.report import HandledError

EnvConfigCreator = Callable[[str], ConfigSet]


@pytest.fixture()
def example(tox_ini_conf: ToxIniCreator) -> EnvConfigCreator:
    def func(conf: str) -> ConfigSet:
        config = tox_ini_conf(f"""[tox]\nenv_list = a\n[testenv]\n{conf}\n""")
        env_config = config.get_env("a")
        return env_config

    return func


def test_replace_within_tox_env(example: EnvConfigCreator) -> None:
    env_config = example("r = 1\no = {r}")
    env_config.add_config(keys="r", of_type=str, default="r", desc="r")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "1"


def test_replace_within_tox_env_missing_raises(example: EnvConfigCreator) -> None:
    env_config = example("o = {p}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")

    assert env_config["o"] == "{p}"


def test_replace_within_tox_env_missing_default(example: EnvConfigCreator) -> None:
    env_config = example("o = {p:one}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_within_tox_env_missing_default_env_only(example: EnvConfigCreator) -> None:
    env_config = example("o = {[testenv:a]p:one}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_within_tox_env_missing_no_default(example: EnvConfigCreator) -> None:
    env_config = example("o = {[testenv:b]p}")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    assert env_config["o"] == "{[testenv:b]p}"


def test_replace_within_tox_env_from_base(example: EnvConfigCreator) -> None:
    env_config = example("p = one\n[testenv:a]\no = {[testenv]p}")
    env_config.add_config(keys="p", of_type=str, default="p", desc="p")
    env_config.add_config(keys="o", of_type=str, default="o", desc="o")
    result = env_config["o"]
    assert result == "one"


def test_replace_ref_bad_type(tox_ini_conf: ToxIniCreator) -> None:
    config = tox_ini_conf("[testenv:a]\nx = {[testenv:b]v}\n[testenv:b]\nv=1")

    class BadType:
        def __init__(self, value: str) -> None:
            if value != "magic":
                raise ValueError(value)

    conf_b = config.get_env("b")
    conf_b.add_config(keys="v", of_type=BadType, default=BadType("magic"), desc="p")

    conf_a = config.get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")

    with pytest.raises(HandledError, match=r"replace failed in a.x with ValueError.*'1'.*"):
        assert conf_a["x"]


@pytest.mark.parametrize(
    ["start", "end"],
    [
        ("0", "0"),
        ("0}", "0}"),
        ("{0", "{0"),
        ("{0}", "{0}"),
        ("{}{0}", "{}{0}"),
        ("{0}{}", "{0}{}"),
        ("\\{0}", "{0}"),
        ("{0\\}", "{0}"),
        ("\\{0\\}", "{0}"),
        ("f\\{0\\}", "f{0}"),
        ("\\{0\\}f", "{0}f"),
        ("\\{\\{0", "{{0"),
        ("0\\}\\}", "0}}"),
        ("\\{\\{0\\}\\}", "{{0}}"),
    ],
)
def test_do_not_replace(replace_one: ReplaceOne, start: str, end: str) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    value = replace_one(start)
    assert value == end


def test_replace_from_tox_section_non_registered(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[tox]\na=1\n[testenv:a]\nx = {[tox]a}").get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")
    assert conf_a["x"] == "1"


def test_replace_from_tox_section_missing_section(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:a]\nx = {[magic]a}").get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")
    assert conf_a["x"] == "{[magic]a}"


def test_replace_circular(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:a]\nx = {y}\ny = {x}").get_env("a")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="o")
    conf_a.add_config(keys="y", of_type=str, default="n", desc="n")
    with pytest.raises(HandledError) as exc:
        assert conf_a["x"]
    assert "circular chain detected x, y" in str(exc.value)


def test_replace_from_tox_section_missing_value(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:e]\nx = {[m]a}\n[m]").get_env("e")
    conf_a.add_config(keys="x", of_type=str, default="o", desc="d")
    assert conf_a["x"] == "{[m]a}"


def test_replace_from_section_bad_type(tox_ini_conf: ToxIniCreator) -> None:
    conf_a = tox_ini_conf("[testenv:e]\nx = {[m]a}\n[m]\na=w\n").get_env("e")
    conf_a.add_config(keys="x", of_type=int, default=1, desc="d")
    with pytest.raises(ValueError, match="invalid literal.*w.*"):
        assert conf_a["x"]


def test_replace_from_tox_section_registered(tox_ini_conf: ToxIniCreator, tmp_path: Path) -> None:
    conf_a = tox_ini_conf("[testenv:a]\nx = {[tox]tox_root}").get_env("a")
    conf_a.add_config(keys="x", of_type=Path, default=Path.cwd() / "magic", desc="d")
    assert conf_a["x"] == (tmp_path / "c")
