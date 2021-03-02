import pytest


def test_getpath(get_option):
    changedir = get_option(
        """
        [testenv]
        changedir = []
        """,
        "changedir",
    )
    assert str(changedir)[-2:] == "[]"


@pytest.fixture
def get_option(newconfig):
    def do(tox_ini, option_name):
        config = newconfig([], tox_ini)
        print(type(config.envconfigs), config.envconfigs.keys())
        return getattr(config.envconfigs["python"], option_name)

    return do
