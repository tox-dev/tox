from tox.pytest import ToxProjectCreator


def test_setuptools_project_no_package(tox_project: ToxProjectCreator):
    project = tox_project(
        {
            "tox.ini": """
        [tox]
        env_list = py
        no_package = true

        [testenv]
        deps = pip
        commands_pre =
            python -c 'import sys; print("start", sys.executable)'
        commands =
            python -c 'import sys; print("do", sys.executable)'
        commands_post =
            python -c 'import sys; print("end", sys.executable)'
        """
        }
    )
    outcome = project.run("-e", "py")
    outcome.assert_success()
