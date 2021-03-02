import pytest

import tox


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


def test_getfloat(get_option):
    """[] is not substituted in options of type float"""
    with pytest.raises(tox.exception.ConfigError):
        get_option(
            """
            [testenv]
            interrupt_timeout = []
            """,
            "interrupt_timeout",
        )


def test_getbool(get_option):
    """[] is not substituted in options of type bool"""
    with pytest.raises(tox.exception.ConfigError):
        get_option(
            """
            [testenv]
            ignore_outcome = []
            """,
            "ignore_outcome",
        )


def test_getargvlist(get_option):
    """[] is substituted in options of type argvlist"""
    value = get_option(
        """
        [testenv]
        commands = foo []
        """,
        "commands",
    )
    assert value == [["foo"]]


def test_getargvlist_nonempty(get_option):
    """[] is substituted in options of type argvlist"""
    value = get_option(
        """
        [testenv]
        commands = foo []
        """,
        "commands",
        ["bar"],
    )
    assert value == [["foo", "bar"]]


def test_getargv(get_option):
    """[] is substituted in options of type argv"""
    value = get_option(
        """
        [testenv]
        list_dependencies_command = foo []
        """,
        "list_dependencies_command",
        ["bar"],
    )
    assert value == ["foo", "bar"]


def test_getargv_install_command(get_option):
    """[] is substituted in options of type argv_install_command"""
    value = get_option(
        """
        [testenv]
        install_command = foo [] {packages}
        """,
        "install_command",
        ["bar"],
    )
    assert value == ["foo", "bar", "{packages}"]


def test_getstring(get_option):
    """[] is not substituted in options of type string"""
    value = get_option(
        """
        [testenv]
        description = []
        """,
        "description",
    )
    assert value == "[]"


@pytest.mark.parametrize(
    ("value", "result"),
    [
        ("x[]", "x[]"),  # no substitution inside a word
        ("[]x", "[]x"),  # no substitution inside a word
        ("{envname}[]", "pythonbar"),  # {envname} and [] are two separate words
        ("[]{envname}", "barpython"),  # {envname} and [] are two separate words
    ],
)
def test_examples(value, result, get_option):
    got = get_option(
        """
        [testenv]
        list_dependencies_command = foo %s
        """
        % value,
        "list_dependencies_command",
        ["bar"],
    )
    assert got == ["foo", result]


@pytest.fixture
def get_option(newconfig):
    def do(tox_ini, option_name, pos_args=()):
        config = newconfig(list(pos_args), tox_ini)
        print(type(config.envconfigs), config.envconfigs.keys())
        return getattr(config.envconfigs["python"], option_name)

    return do
