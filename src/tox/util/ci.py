from __future__ import annotations

import os

_ENV_VARS = {  # per https://adamj.eu/tech/2020/03/09/detect-if-your-tests-are-running-on-ci
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
}


def is_ci() -> bool:
    """:return: a flag indicating if running inside a CI env or not"""
    return any(e in os.environ if v is None else os.environ.get(e) == v for e, v in _ENV_VARS.items())


__all__ = [
    "is_ci",
]
