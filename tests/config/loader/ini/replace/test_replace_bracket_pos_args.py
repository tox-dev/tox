import pytest

import tox


def test_get_path(get_option):
    """[] is not substituted in options of type path"""
    value = get_option(
        """
        [testenv]
        changedir = []
        """,
        "changedir",
    )
    assert str(value)[-2:] == "[]"


def test_get_list(get_option):
    """[] is not substituted in options of type list"""
    value = get_option(
        """
        [testenv]
        allowlist_externals = []
        """,
        "allowlist_externals",
    )
    assert value == ["[]"]


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


def test_get_float(get_option):
    """[] is not substituted in options of type float"""
    with pytest.raises(tox.exception.ConfigError):
        get_option(
            """
            [testenv]
            interrupt_timeout = []
            """,
            "interrupt_timeout",
        )


def test_get_bool(get_option):
    """[] is not substituted in options of type bool"""
    with pytest.raises(tox.exception.ConfigError):
        get_option(
            """
            [testenv]
            ignore_outcome = []
            """,
            "ignore_outcome",
        )


def test_get_argv_list(get_option):
    """[] is substituted in options of type argvlist"""
    value = get_option(
        """
        [testenv]
        commands = foo []
        """,
        "commands",
    )
    assert value == [["foo"]]


def test_get_argv_list_nonempty(get_option):
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


def test_get_argv(get_option):
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


def test_get_argv_install_command(get_option):
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


def test_get_string(get_option):
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
        ("{envname}[]", "pythonbar"),  # noqa: SC100 {envname} and [] are two separate words
        ("[]{envname}", "barpython"),  # noqa: SC100 {envname} and [] are two separate words
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


def test_no_substitutions_inside_pos_args(get_option):
    got = get_option(
        """
        [testenv]
        list_dependencies_command = foo []
        """,
        "list_dependencies_command",
        ["{envname}"],
    )
    assert got == ["foo", "{envname}"]


def test_no_pos_args_inside_substitutions(get_option, monkeypatch):
    monkeypatch.setenv("BAZ", "[]")
    got = get_option(
        """
        [testenv]
        list_dependencies_command = foo {env:BAZ}
        """,
        "list_dependencies_command",
        ["bar"],
    )
    assert got == ["foo", "[]"]
