import pytest

from tests.config.ini.replace.conftest import ReplaceOne


@pytest.mark.parametrize(
    ["start", "end"],
    [
        ("0", "0"),
        ("\\{0}", "{0}"),
        ("{0\\}", "{0}"),
        ("\\{0\\}", "{0}"),
        ("f\\{0\\}", "f{0}"),
        ("\\{0\\}f", "{0}f"),
        ("\\{\\{0", "{{0"),
        ("0\\}\\}", "0}}"),
        ("\\{\\{0\\}\\}", "{{0}}"),
    ],
)
def test_do_not_replace(replace_one: ReplaceOne, start: str, end: str) -> None:
    """If we have a factor that is not specified within the core env-list then that's also an environment"""
    with replace_one(start) as result:
        pass
    assert result.val == end
