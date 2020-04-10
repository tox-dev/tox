import sys

from tox.config.source.api import EnvList
from tox.pytest import ToxProjectCreator


def test_build_env_basic(tox_project: ToxProjectCreator):
    py_ver = sys.version_info[0:2]
    project = tox_project(
        {
            "tox.ini": """
    [tox]
    env_list = py{}{}
    """.format(
                *py_ver
            ),
        },
    )
    result = project.run("c")
    state = result.state
    assert state.args == ("c",)
    assert state.env_list == EnvList(["py{}{}".format(*py_ver)])
