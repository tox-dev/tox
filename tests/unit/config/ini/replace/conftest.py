from contextlib import contextmanager

import pytest

from tox.pytest import ToxProjectCreator


@pytest.fixture
def replace_one(tox_project: ToxProjectCreator):
    @contextmanager
    def example(conf):
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

        class Result:
            def __init__(self):
                self.config = None
                self.val = None

        result = Result()
        yield result
        result.config = project.config()
        env_config = result.config["a"]
        env_config.add_config(keys="env", of_type=str, default="bad", desc="env")
        result.val = env_config["env"]

    return example
