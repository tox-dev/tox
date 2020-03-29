import os
import textwrap

from tox.version import __version__


def test_list_empty(tox_project):
    project = tox_project({"tox.ini": ""})
    outcome = project.run("c")
    outcome.assert_success()

    expected = textwrap.dedent(
        """
        [tox]
        base = 
        tox_root = {0}
        work_dir = {0}{1}.tox
        temp_dir = {0}{1}.temp
        env_list = 
        skip_missing_interpreters = True
        min_version = {2}
        provision_tox_env = .tox
        requires = 
          tox>={2}
        no_package = False
        """.format(
            project.path, os.sep, __version__,
        ),
    ).lstrip()
    assert outcome.out == expected
