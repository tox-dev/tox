import pytest

from tox.pytest import ToxProjectCreator


@pytest.mark.plugin_test
def test_inline_tox_py(tox_project: ToxProjectCreator) -> None:
    ini = """
    from tox.plugin.impl import impl
    @impl
    def tox_add_option(parser):
        parser.add_argument("--magic", action="store_true")
    """
    project = tox_project({"tox_.py": ini})
    result = project.run("-h")
    result.assert_success()
    assert "--magic" in result.out
