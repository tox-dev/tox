import pytest

from tox.config.cli.parser import Parsed, ToxParser


def test_parser_const_with_default_none(monkeypatch):
    monkeypatch.setenv("TOX_ALPHA", "2")
    parser = ToxParser.base()
    parser.add_argument(
        "-a",
        dest="alpha",
        action="store_const",
        const=1,
        default=None,
        help="sum the integers (default: find the max)",
    )
    parser.fix_defaults()

    result, _ = parser.parse([])
    assert result.alpha == 2


@pytest.mark.parametrize("is_atty", [True, False])
@pytest.mark.parametrize("no_color", [None, "0", "1"])
@pytest.mark.parametrize("force_color", [None, "0", "1"])
@pytest.mark.parametrize("tox_color", [None, "bad", "no", "yes"])
def test_parser_color(monkeypatch, mocker, no_color, force_color, tox_color, is_atty):
    for key, value in {"NO_COLOR": no_color, "TOX_COLORED": tox_color, "FORCE_COLOR": force_color}.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    stdout_mock = mocker.patch("tox.config.cli.parser.sys.stdout")
    stdout_mock.isatty.return_value = is_atty

    if tox_color in ("yes", "no"):
        expected = True if tox_color == "yes" else False
    elif no_color == "1":
        expected = False
    elif force_color == "1":
        expected = True
    else:
        expected = is_atty

    is_colored = ToxParser.base().parse_args([], Parsed()).is_colored
    assert is_colored is expected
