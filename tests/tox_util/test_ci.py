from __future__ import annotations

import operator
import os

import pytest

from tox.util.ci import is_ci


@pytest.mark.parametrize(
    "env_var",
    {
        "CI": "true",  # generic flag
        "TF_BUILD": "true",  # Azure Pipelines
        "bamboo.buildKey": None,  # Bamboo
        "BUILDKITE": "true",  # Buildkite
        "CIRCLECI": "true",  # Circle CI
        "CIRRUS_CI": "true",  # Cirrus CI
        "CODEBUILD_BUILD_ID": None,  # CodeBuild
        "GITHUB_ACTIONS": "true",  # GitHub Actions
        "GITLAB_CI": None,  # GitLab CI
        "HEROKU_TEST_RUN_ID": None,  # Heroku CI
        "BUILD_ID": None,  # Hudson
        "TEAMCITY_VERSION": None,  # TeamCity
        "TRAVIS": "true",  # Travis CI
    }.items(),
    ids=operator.itemgetter(0),
)
def test_is_ci(env_var: tuple[str, str | None], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "environ", {})
    monkeypatch.setenv(env_var[0], env_var[1] or "")
    assert is_ci()


@pytest.mark.parametrize(
    "env_var",
    {
        "TF_BUILD": "",  # Azure Pipelines
        "BUILDKITE": "",  # Buildkite
        "CIRCLECI": "",  # Circle CI
        "CIRRUS_CI": "",  # Cirrus CI
        "GITHUB_ACTIONS": "",  # GitHub Actions
        "TRAVIS": "",  # Travis CI
    }.items(),
    ids=operator.itemgetter(0),
)
def test_is_ci_bad_set(env_var: tuple[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "environ", {})
    monkeypatch.setenv(env_var[0], env_var[1])
    assert not is_ci()


def test_is_ci_not(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "environ", {})
    assert not is_ci()


def test_is_ci_not_teamcity_local(monkeypatch: pytest.MonkeyPatch) -> None:
    # pycharm sets this
    monkeypatch.setattr(os, "environ", {})

    monkeypatch.setenv("TEAMCITY_VERSION", "LOCAL")
    assert not is_ci()


@pytest.mark.parametrize("value", ["false", "0", ""])
def test_is_ci_generic_flag_opted_out(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "environ", {})
    monkeypatch.setenv("CI", value)

    assert is_ci() is False
