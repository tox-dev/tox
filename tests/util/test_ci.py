from __future__ import annotations

import operator

import pytest

from tox.util.ci import _ENV_VARS, is_ci  # noqa: PLC2701


@pytest.mark.parametrize(
    "env_var",
    {
        "CI": None,  # generic flag
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
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)
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
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv(env_var[0], env_var[1])
    assert not is_ci()


def test_is_ci_not(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    assert not is_ci()


def test_is_ci_not_teamcity_local(monkeypatch: pytest.MonkeyPatch) -> None:
    # pycharm sets this
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    monkeypatch.setenv("TEAMCITY_VERSION", "LOCAL")
    assert not is_ci()
