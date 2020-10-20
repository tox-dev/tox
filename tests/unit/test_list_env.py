import os
import textwrap

from tox.version import __version__


def test_list_empty(tox_project):
    project = tox_project({"tox.ini": ""})
    outcome = project.run("c")
    outcome.assert_success()

    expected = textwrap.dedent(
        f"""
        [tox]
        tox_root = {project.path}
        work_dir = {project.path}{os.sep}.tox
        temp_dir = {project.path}{os.sep}.temp
        env_list =
        skip_missing_interpreters = True
        min_version = {__version__}
        provision_tox_env = .tox
        requires =
          tox>={__version__}
        no_package = False
        """,
    ).lstrip()
    assert outcome.out == expected
