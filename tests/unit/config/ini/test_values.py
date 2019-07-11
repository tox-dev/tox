from tox.config.source.api import Command
from tox.pytest import ToxProjectCreator


def test_commands(tox_project: ToxProjectCreator):
    project = tox_project(
        {
            "tox.ini": """
        [tox]
        env_list = py
        no_package = true
        [testenv]
        commands_pre =
            python -c 'import sys; print("start", sys.executable)'
        commands =
            pip config list
            pip list
        commands_post =
            python -c 'import sys; print("end", sys.executable)'
        """
        }
    )
    outcome = project.run("c")
    outcome.assert_success()
    env_config = outcome.state.tox_envs["py"].conf
    assert env_config["commands_pre"] == [
        Command(args=["python", "-c", 'import sys; print("start", sys.executable)'])
    ]
    assert env_config["commands"] == [
        Command(args=["pip", "config", "list"]),
        Command(args=["pip", "list"]),
    ]
    assert env_config["commands_post"] == [
        Command(args=["python", "-c", 'import sys; print("end", sys.executable)'])
    ]
