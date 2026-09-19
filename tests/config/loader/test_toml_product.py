from __future__ import annotations

import textwrap
from typing import TYPE_CHECKING

import pytest

from tox.config.loader.ini.factor import LATEST_PYTHON_MINOR_MAX, LATEST_PYTHON_MINOR_MIN
from tox.config.loader.toml._product import (  # ruff:ignore[import-private-name]
    _expand_range,
    expand_factor_group,
    expand_product,
    extract_default,
    extract_label,
)

if TYPE_CHECKING:
    from tox.config.loader.toml._api import TomlTypes
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


def test_expand_product_exclude_not_list() -> None:
    with pytest.raises(TypeError, match="product exclude must be a list, got str"):
        expand_product({"product": [["a"]], "exclude": "a"})


def test_expand_factor_group_list() -> None:
    assert expand_factor_group(["py312", "py313"]) == ["py312", "py313"]


def test_expand_factor_group_range_dict() -> None:
    assert expand_factor_group({"prefix": "py3", "start": 12, "stop": 14}) == ["py312", "py313", "py314"]


def test_expand_factor_group_bad_type() -> None:
    with pytest.raises(TypeError, match="factor group must be a list, a range dict, or a labeled dict"):
        expand_factor_group(42)


def test_expand_factor_group_dict_no_prefix() -> None:
    with pytest.raises(TypeError, match="factor group must be a list, a range dict, or a labeled dict"):
        expand_factor_group({"start": 1, "stop": 3})


def test_expand_factor_group_list_with_dict_item_hints_unnesting() -> None:
    with pytest.raises(TypeError, match=r"factor group list items must be strings, got dict.*sibling factor groups"):
        expand_factor_group([{"prefix": "py3", "start": 9, "stop": 14}])


def test_expand_factor_group_list_with_int_item_plain_error() -> None:
    with pytest.raises(TypeError, match=r"factor group list items must be strings, got int$"):
        expand_factor_group(["py312", 42])


def test_expand_factor_group_keyed_dict() -> None:
    assert expand_factor_group({"ecosystem": ["oci", "python"]}) == ["oci", "python"]


def test_expand_factor_group_keyed_dict_bad_value_type() -> None:
    with pytest.raises(TypeError, match="labeled factor group 'ecosystem' must map to a list, a range dict, or a"):
        expand_factor_group({"ecosystem": "oci"})


def test_expand_factor_group_keyed_range_dict() -> None:
    assert expand_factor_group({"py_version": {"prefix": "3.", "start": 12, "stop": 14}}) == ["3.12", "3.13", "3.14"]


def test_extract_label_keyed_range_dict() -> None:
    assert extract_label({"py_version": {"prefix": "3.", "start": 12}}) == "py_version"


def test_expand_factor_group_reserved_label() -> None:
    with pytest.raises(TypeError, match="'env' is reserved and cannot be used as a factor label"):
        expand_factor_group({"env": ["a", "b"]})


def test_expand_factor_group_reserved_label_factor() -> None:
    with pytest.raises(TypeError, match="'factor' is reserved and cannot be used as a factor label"):
        expand_factor_group({"factor": ["a", "b"]})


def test_expand_factor_group_keyed_values_dict() -> None:
    assert expand_factor_group({"django_version": {"values": ["django42", "django50"]}}) == ["django42", "django50"]


def test_expand_factor_group_keyed_values_not_a_list() -> None:
    with pytest.raises(TypeError, match="labeled factor group 'django_version' 'values' must be a list, got str"):
        expand_factor_group({"django_version": {"values": "django42"}})


def test_expand_factor_group_keyed_dict_without_prefix_or_values() -> None:
    with pytest.raises(TypeError, match="labeled factor group 'py_version' maps to a dict with neither a 'prefix'"):
        expand_factor_group({"py_version": {"start": 12, "stop": 14}})


@pytest.mark.parametrize(
    ("group", "values", "expected"),
    [
        pytest.param(
            {"django_version": {"values": ["django42", "django50"], "default": "django50"}},
            ["django42", "django50"],
            "django50",
            id="values-dict",
        ),
        pytest.param(
            {"prefix": "py3", "start": 12, "stop": 13, "default": "py313"},
            ["py312", "py313"],
            "py313",
            id="range-dict",
        ),
        pytest.param({"ecosystem": ["oci", "python"]}, ["oci", "python"], None, id="labeled-list"),
        pytest.param(["oci", "python"], ["oci", "python"], None, id="plain-list"),
    ],
)
def test_extract_default(group: TomlTypes, values: list[str], expected: str | None) -> None:
    assert extract_default(group, values) == expected


@pytest.mark.parametrize(
    ("group", "values", "message"),
    [
        pytest.param(
            {"py_version": {"values": ["a"], "default": 3}},
            ["a"],
            "factor group 'default' must be a string, got int",
            id="not-a-string",
        ),
        pytest.param(
            {"py_version": {"values": ["a", "b"], "default": "nope"}},
            ["a", "b"],
            "factor group 'default' 'nope' is not one of its factors: a, b",
            id="not-a-factor",
        ),
    ],
)
def test_extract_default_invalid(group: TomlTypes, values: list[str], message: str) -> None:
    with pytest.raises(TypeError, match=message):
        extract_default(group, values)


def test_extract_label_keyed_dict() -> None:
    assert extract_label({"ecosystem": ["oci", "python"]}) == "ecosystem"


def test_extract_label_plain_list() -> None:
    assert extract_label(["oci", "python"]) is None


def test_extract_label_range_dict() -> None:
    assert extract_label({"prefix": "py3", "start": 12, "stop": 14}) is None


def test_extract_label_multi_key_dict() -> None:
    assert extract_label({"a": [1], "b": [2]}) is None


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


@pytest.mark.parametrize("key", ["start", "stop"])
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("13", id="str"),
        pytest.param(13.0, id="float"),
        pytest.param(True, id="true"),
        pytest.param(False, id="false"),
    ],
)
def test_expand_range_bound_not_int(key: str, value: TomlTypes) -> None:
    with pytest.raises(TypeError, match=f"range '{key}' must be an integer, got {type(value).__name__}"):
        _expand_range({"prefix": "py3", "start": 12, "stop": 14, key: value})


def test_expand_product_mixed_list_and_range() -> None:
    result = expand_product({
        "product": [
            {"prefix": "py3", "start": 12, "stop": 13},
            ["django42", "django50"],
        ],
    })
    assert result == ["py312-django42", "py312-django50", "py313-django42", "py313-django50"]


@pytest.mark.parametrize(
    ("env_list", "present", "absent"),
    [
        pytest.param(
            '{ product = [["py312", "py313"], ["django42", "django50"]] }',
            ["py312-django42", "py312-django50", "py313-django42", "py313-django50"],
            [],
            id="product",
        ),
        pytest.param(
            '"lint", { product = [["py312", "py313"], ["django42"]] }, "docs"',
            ["lint", "py312-django42", "py313-django42", "docs"],
            [],
            id="product-mixed-with-literals",
        ),
        pytest.param(
            '{ product = [{ prefix = "py3", start = 12, stop = 13 }, ["django42"]] }',
            ["py312-django42", "py313-django42"],
            [],
            id="product-with-range",
        ),
        pytest.param(
            '{ product = [["py312", "py313"], ["django42", "django50"]], exclude = ["py312-django50"] }',
            ["py312-django42", "py313-django42", "py313-django50"],
            ["py312-django50"],
            id="product-with-exclusion",
        ),
        pytest.param(
            '{ product = [["py312"], ["django42"]] }, { product = [["py313"], ["flask20"]] }',
            ["py312-django42", "py313-flask20"],
            [],
            id="multiple-products",
        ),
        pytest.param(
            '{ product = [["sync"], {ecosystem = ["oci", "python"]}, {target = ["pw", "tt"]}] }',
            ["sync-oci-pw", "sync-oci-tt", "sync-python-pw", "sync-python-tt"],
            [],
            id="product-keyed-groups",
        ),
        pytest.param(
            '"lint", { prefix = "py3", start = 12, stop = 14 }',
            ["lint", "py312", "py313", "py314"],
            [],
            id="bare-range-dict",
        ),
        pytest.param('{ ecosystem = ["oci", "python"] }', ["oci", "python"], [], id="bare-labeled-dict"),
        pytest.param(
            (
                '{ prefix = "py3", start = 12, stop = 13 }, '
                '{ product = [["min"], { prefix = "py3", start = 12, stop = 13 }] }'
            ),
            ["py312", "py313", "min-py312", "min-py313"],
            [],
            id="bare-range-mixed-with-product",
        ),
    ],
)
def test_env_list_lists_expected_envs(
    tox_project: ToxProjectCreator, env_list: str, present: list[str], absent: list[str]
) -> None:
    tox_toml = f"""\
        env_list = [{env_list}]

        [env_run_base]
        package = "skip"
        commands = [["python", "-c", "print('ok')"]]
    """
    result = tox_project({"tox.toml": textwrap.dedent(tox_toml)}).run("l")
    result.assert_success()
    assert [env for env in present if env in result.out] == present
    assert [env for env in absent if env in result.out] == []


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
