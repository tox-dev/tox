from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

from tox.config.loader.ini.factor import LATEST_PYTHON_MINOR_MAX, LATEST_PYTHON_MINOR_MIN
from tox.config.loader.toml._product import (
    _expand_factor_group,  # noqa: PLC2701
    _expand_range,  # noqa: PLC2701
    expand_product,  # noqa: PLC2701
)

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


def test_expand_product_two_groups() -> None:
    result = expand_product({"product": [["a", "b"], ["x", "y"]]})
    assert result == ["a-x", "a-y", "b-x", "b-y"]


def test_expand_product_three_groups() -> None:
    result = expand_product({"product": [["a"], ["b", "c"], ["d"]]})
    assert result == ["a-b-d", "a-c-d"]


def test_expand_product_single_group() -> None:
    result = expand_product({"product": [["a", "b"]]})
    assert result == ["a", "b"]


def test_expand_product_empty() -> None:
    assert expand_product({"product": []}) == []


def test_expand_product_with_exclusion() -> None:
    result = expand_product({"product": [["a", "b"], ["x", "y"]], "exclude": ["a-y", "b-x"]})
    assert result == ["a-x", "b-y"]


def test_expand_product_exclusion_miss_is_ignored() -> None:
    result = expand_product({"product": [["a"], ["x"]], "exclude": ["nonexistent"]})
    assert result == ["a-x"]


def test_expand_product_not_list() -> None:
    with pytest.raises(TypeError, match="product value must be a list"):
        expand_product({"product": "bad"})


def test_expand_factor_group_list() -> None:
    assert _expand_factor_group(["py312", "py313"]) == ["py312", "py313"]


def test_expand_factor_group_range_dict() -> None:
    assert _expand_factor_group({"prefix": "py3", "start": 12, "stop": 14}) == ["py312", "py313", "py314"]


def test_expand_factor_group_bad_type() -> None:
    with pytest.raises(TypeError, match="factor group must be a list of strings or a range dict"):
        _expand_factor_group(42)


def test_expand_factor_group_dict_no_prefix() -> None:
    with pytest.raises(TypeError, match="factor group must be a list of strings or a range dict"):
        _expand_factor_group({"start": 1, "stop": 3})


def test_expand_range_closed() -> None:
    assert _expand_range({"prefix": "py3", "start": 12, "stop": 14}) == ["py312", "py313", "py314"]


def test_expand_range_open_stop() -> None:
    result = _expand_range({"prefix": "py3", "start": 12})
    assert result == [f"py3{i}" for i in range(12, LATEST_PYTHON_MINOR_MAX + 1)]


def test_expand_range_open_start() -> None:
    result = _expand_range({"prefix": "py3", "stop": 13})
    assert result == [f"py3{i}" for i in range(LATEST_PYTHON_MINOR_MIN, 14)]


def test_expand_range_no_bounds() -> None:
    with pytest.raises(TypeError, match="range must have at least 'start' or 'stop'"):
        _expand_range({"prefix": "py3"})


def test_expand_range_start_not_int() -> None:
    with pytest.raises(TypeError, match="range 'start' must be an integer"):
        _expand_range({"prefix": "py3", "start": "12", "stop": 14})


def test_expand_range_stop_not_int() -> None:
    with pytest.raises(TypeError, match="range 'stop' must be an integer"):
        _expand_range({"prefix": "py3", "start": 12, "stop": "14"})


def test_expand_product_mixed_list_and_range() -> None:
    result = expand_product({
        "product": [
            {"prefix": "py3", "start": 12, "stop": 13},
            ["django42", "django50"],
        ],
    })
    assert result == ["py312-django42", "py312-django50", "py313-django42", "py313-django50"]


def test_product_envs_listed(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            env_list = [
                { product = [["py312", "py313"], ["django42", "django50"]] },
            ]

            [env_run_base]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = proj.run("l")
    result.assert_success()
    for env in ("py312-django42", "py312-django50", "py313-django42", "py313-django50"):
        assert env in result.out


def test_product_mixed_with_literals(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            env_list = [
                "lint",
                { product = [["py312", "py313"], ["django42"]] },
                "docs",
            ]

            [env_run_base]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = proj.run("l")
    result.assert_success()
    for env in ("lint", "py312-django42", "py313-django42", "docs"):
        assert env in result.out


def test_product_with_range(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            env_list = [
                { product = [{ prefix = "py3", start = 12, stop = 13 }, ["django42"]] },
            ]

            [env_run_base]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = proj.run("l")
    result.assert_success()
    assert "py312-django42" in result.out
    assert "py313-django42" in result.out


def test_product_with_exclusion(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            env_list = [
                { product = [["py312", "py313"], ["django42", "django50"]], exclude = ["py312-django50"] },
            ]

            [env_run_base]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = proj.run("l")
    result.assert_success()
    assert "py312-django42" in result.out
    assert "py313-django42" in result.out
    assert "py313-django50" in result.out
    assert "py312-django50" not in result.out


def test_product_multiple_in_env_list(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            env_list = [
                { product = [["py312"], ["django42"]] },
                { product = [["py313"], ["flask20"]] },
            ]

            [env_run_base]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = proj.run("l")
    result.assert_success()
    assert "py312-django42" in result.out
    assert "py313-flask20" in result.out


def test_product_deduplication(tox_project: ToxProjectCreator) -> None:
    proj = tox_project({
        "tox.toml": textwrap.dedent("""\
            env_list = [
                "py312-django42",
                { product = [["py312"], ["django42"]] },
            ]

            [env_run_base]
            package = "skip"
            commands = [["python", "-c", "print('ok')"]]
        """),
    })
    result = proj.run("l")
    result.assert_success()
    assert result.out.count("py312-django42") == 1
