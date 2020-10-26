import platform
import sys

from tox.config.source.api import EnvList
from tox.pytest import ToxProjectCreator


def test_build_env_basic(tox_project: ToxProjectCreator) -> None:
    py_ver = sys.version_info[0:2]
    name = "py{}{}".format(*py_ver) if platform.python_implementation() == "CPython" else "pypy3"
    project = tox_project({"tox.ini": f"[tox]\nenv_list = {name}"})
    result = project.run("c")
    state = result.state
    assert state.args == ("c",)
    assert state.env_list == EnvList([name])
