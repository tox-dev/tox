import pytest


def test_getpath(get_option):
    """[] is not substituted in options of type path"""
    changedir = get_option(
        """
        [testenv]
        changedir = []
        """,
        "changedir",
    )
    assert str(changedir)[-2:] == "[]"


def test_getlist(get_option):
    """[] is not substituted in options of type list"""
    value = get_option(
        """
        [testenv]
        allowlist_externals = []
        """,
        "allowlist_externals",
    )
    assert value == ["[]"]


def test_getdict(get_option):
    """[] is not substituted in options of type dict"""
    # TODO


def test_dict_setenv(get_option):
    """[] is not substituted in options of type dict_setenv"""
    value = get_option(
        """
        [testenv]
        setenv =
          FOO = []
        """,
        "setenv",
    )
    assert value["FOO"] == "[]"


@pytest.fixture
def get_option(newconfig):
    def do(tox_ini, option_name):
        config = newconfig([], tox_ini)
        print(type(config.envconfigs), config.envconfigs.keys())
        return getattr(config.envconfigs["python"], option_name)

    return do
