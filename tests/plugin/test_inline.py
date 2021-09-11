import pytest

from tox.pytest import ToxProjectCreator


@pytest.mark.plugin_test()
def test_inline_tox_py(tox_project: ToxProjectCreator) -> None:
    def plugin() -> None:  # pragma: no cover # the code is copied to a python file
        import logging

        from tox.config.cli.parser import ToxParser
        from tox.plugin import impl

        @impl
        def tox_add_option(parser: ToxParser) -> None:
            logging.warning("Add magic")
            parser.add_argument("--magic", action="store_true")

    project = tox_project({"toxfile.py": plugin})
    result = project.run("-h")
    result.assert_success()
    assert "--magic" in result.out


@pytest.mark.plugin_test()
def test_plugin_hooks(tox_project: ToxProjectCreator) -> None:
    def plugin() -> None:  # pragma: no cover # the code is copied to a python file
        import logging
        from typing import List

        from tox.config.cli.parser import ToxParser
        from tox.config.main import Config
        from tox.config.sets import ConfigSet
        from tox.execute import Outcome
        from tox.plugin import impl
        from tox.tox_env.api import ToxEnv
        from tox.tox_env.register import ToxEnvRegister

        @impl
        def tox_register_tox_env(register: ToxEnvRegister) -> None:
            assert isinstance(register, ToxEnvRegister)
            logging.warning("tox_register_tox_env")

        @impl
        def tox_add_option(parser: ToxParser) -> None:
            assert isinstance(parser, ToxParser)
            logging.warning("tox_add_option")

        @impl
        def tox_add_core_config(core: ConfigSet) -> None:
            assert isinstance(core, ConfigSet)
            logging.warning("tox_add_core_config")

        @impl
        def tox_configure(config: Config) -> None:
            assert isinstance(config, Config)
            logging.warning("tox_configure")

        @impl
        def tox_before_run_commands(tox_env: ToxEnv) -> None:
            assert isinstance(tox_env, ToxEnv)
            logging.warning("tox_before_run_commands")

        @impl
        def tox_after_run_commands(tox_env: ToxEnv, exit_code: int, outcomes: List[Outcome]) -> None:
            assert isinstance(tox_env, ToxEnv)
            assert exit_code == 0
            assert isinstance(outcomes, list)
            assert all(isinstance(i, Outcome) for i in outcomes)
            logging.warning("tox_after_run_commands")

    project = tox_project({"toxfile.py": plugin, "tox.ini": "[testenv]\npackage=skip\ncommands=python -c 'print(1)'"})
    result = project.run("r")
    result.assert_success()
    output = r"""
    ROOT: tox_register_tox_env
    ROOT: tox_add_option
    ROOT: tox_configure
    ROOT: tox_add_core_config
    py: tox_before_run_commands
    py: commands\[0\]> python -c .*
    1.*
    py: tox_after_run_commands
      py: OK \(.* seconds\)
      congratulations :\) \(.* seconds\)
    """
    result.assert_out_err(output, err="", dedent=True, regex=True)
