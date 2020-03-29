from tox.config.source.api import EnvList
from tox.pytest import ToxProjectCreator


def test_build_env_basic(tox_project: ToxProjectCreator):
    project = tox_project(
        {
            "tox.ini": """
    [tox]
    env_list = py38, py38
    """,
        },
    )
    result = project.run("c")
    state = result.state
    assert state.args == ("c",)
    assert state.env_list == EnvList(["py38"])
