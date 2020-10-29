import sys
from typing import List, Optional, cast

import pytest

from tox.pytest import ToxProjectCreator

if sys.version_info > (3, 7):
    from typing import Protocol
else:
    from typing_extensions import Protocol


class ReplaceOne(Protocol):
    def __call__(self, conf: str, pos_args: Optional[List[str]] = None) -> str:
        ...


@pytest.fixture
def replace_one(tox_project: ToxProjectCreator) -> ReplaceOne:
    def example(conf: str, pos_args: Optional[List[str]] = None) -> str:
        project = tox_project(
            {
                "tox.ini": f"""
            [tox]
            env_list = a
            [testenv]
            env = {conf}


            """,
            },
        )
        config = project.config(pos_args=pos_args)
        env_config = config.get_env("a")
        env_config.add_config(keys="env", of_type=str, default="bad", desc="env")
        return cast(str, env_config["env"])

    return example  # noqa
