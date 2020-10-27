from contextlib import contextmanager
from typing import Callable, ContextManager, Iterator, Optional

import pytest

from tox.config.main import Config
from tox.pytest import ToxProjectCreator


class Result:
    def __init__(self) -> None:
        self.config: Optional[Config] = None
        self.val: Optional[str] = None


ReplaceOne = Callable[[str], ContextManager[Result]]


@pytest.fixture
def replace_one(tox_project: ToxProjectCreator) -> ReplaceOne:
    @contextmanager
    def example(conf: str) -> Iterator[Result]:
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

        result = Result()
        yield result
        result.config = project.config()
        env_config = result.config["a"]
        env_config.add_config(keys="env", of_type=str, default="bad", desc="env")
        result.val = env_config["env"]

    return example
