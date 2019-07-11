from tox.pytest import ToxProjectCreator


def test_setuptools_package_py_project(tox_project: ToxProjectCreator):
    project = tox_project(
        {
            "tox.ini": """
                [tox]
                env_list = py

                [testenv]
                commands_pre =
                    python -c 'import sys; print("start", sys.executable)'
                commands =
                    python -c 'import magic; print(magic.__version__)'
                commands_post =
                    python -c 'import sys; print("end", sys.executable)'
                package = wheel
                """,
            "setup.cfg": """
                [metadata]
                name = magic
                version = 1.2.3
                [options]
                packages = find:
                package_dir =
                    =src
                [options.packages.find]
                where = src
                [bdist_wheel]
                universal = 1
            """,
            "pyproject.toml": """
                [build-system]
                requires = [
                    "setuptools >= 40.0.4",
                    "wheel >= 0.29.0",
                ]
                build-backend = 'setuptools.build_meta'
             """,
            "src": {"magic": {"__init__.py": """__version__ = "1.2.3" """}},
        }
    )
    outcome = project.run("-vv", "r", "-e", "py")
    outcome.assert_success()
    assert "\n1.2.3\n" in outcome.out
