from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize("filename", ["tox.ini", "tox.toml"])
@pytest.mark.parametrize("own", ["missing", "empty", "value"])
@pytest.mark.parametrize("key", ["deps", "pass_env", "passenv", "set_env", "setenv"])
def test_env_override_appends_inherited_value(
    tox_project: ToxProjectCreator, filename: str, own: str, key: str
) -> None:
    canonical = {"passenv": "pass_env", "setenv": "set_env"}.get(key, key)
    is_set_env = canonical == "set_env"
    base = "BASE=base" if is_set_env else "base"
    local = "LOCAL=local" if is_set_env else "local"
    added = "ADDED=added" if is_set_env else "added"
    if filename == "tox.ini":
        config = f"[tox]\nenv_list=a,b\n[testenv]\npackage=skip\n{canonical}={base}\n"
        if own != "missing":
            config += "[testenv:a]\n"
        if own == "value":
            config += f"{canonical}={local}\n"
        namespace = "testenv:a"
    else:
        value = '{BASE="base"}' if is_set_env else '["base"]'
        config = f'env_list=["a", "b"]\n[env_run_base]\npackage="skip"\n{canonical}={value}\n'
        if own != "missing":
            config += "[env.a]\n"
        if own == "value":
            value = '{LOCAL="local"}' if is_set_env else '["local"]'
            config += f"{canonical}={value}\n"
        namespace = "env.a"
    result = tox_project({filename: config}).run("c", "-e", "a,b", "-k", canonical, "-x", f"{namespace}.{key}+={added}")
    result.assert_success()
    selected, sibling = result.out.split("[testenv:b]", 1)
    values = [line.strip() for line in selected.partition("=")[2].splitlines()]
    assert (local if own == "value" else base) in values
    assert added in values
    assert added not in [line.strip() for line in sibling.partition("=")[2].splitlines()]


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param(["testenv:a.deps+=one", "testenv:a.deps+=two"], ["base", "one", "two"], id="append-twice"),
        pytest.param(["testenv:a.deps=one", "testenv:a.deps+=two"], ["one", "two"], id="replace-append"),
        pytest.param(["testenv:a.deps+=one", "testenv:a.deps=two"], ["two"], id="append-replace"),
        pytest.param(["testenv.deps+=one", "testenv:a.deps+=two"], ["base", "one", "two"], id="base-append"),
    ],
)
def test_env_override_inherited_sequence(
    tox_project: ToxProjectCreator, overrides: list[str], expected: list[str]
) -> None:
    result = tox_project({"tox.ini": "[tox]\nenv_list=a\n[testenv]\npackage=skip\ndeps=base\n"}).run(
        "c", "-e", "a", "-k", "deps", *[item for value in overrides for item in ("-x", value)]
    )
    result.assert_success()
    assert [line.strip() for line in result.out.partition("=")[2].splitlines() if line.strip()] == expected


def test_env_override_append_explicit_empty_value(tox_project: ToxProjectCreator) -> None:
    result = tox_project({
        "tox.ini": "[tox]\nenv_list=a\n[testenv]\npackage=skip\ndeps=base\n[testenv:a]\ndeps=\n"
    }).run("c", "-e", "a", "-k", "deps", "-x", "testenv:a.deps+=added")
    result.assert_success()
    assert [line.strip() for line in result.out.partition("=")[2].splitlines() if line.strip()] == ["added"]
