from __future__ import annotations

import os
from typing import Final

# per https://adamj.eu/tech/2020/03/09/detect-if-your-tests-are-running-on-ci
_ENV_VARS: Final[dict[str, str | None]] = {
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
    """:returns: a flag indicating if running inside a CI env or not"""
    opted_out = frozenset({"", "0", "false"})
    for env_key, value in _ENV_VARS.items():
        if env_key in os.environ if value is None else os.environ.get(env_key) == value:
            if env_key == "TEAMCITY_VERSION" and os.environ.get(env_key) == "LOCAL":
                continue
            # the generic flag is the one users toggle: CI=false (or empty) is an explicit opt-out, the
            # vendor-specific variables keep their pure presence semantics
            if env_key == "CI" and os.environ[env_key].lower() in opted_out:
                continue
            return True
    return False


__all__ = [
    "is_ci",
]
