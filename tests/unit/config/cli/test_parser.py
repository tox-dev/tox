from tox.config.cli.parser import ToxParser


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
