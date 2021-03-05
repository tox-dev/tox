from tox.config.loader.ini.replace import new_find_replace_part as find_replace_part


def test_match() -> None:
    start, end, to_replace = find_replace_part("[]", 0)
    assert start == 0
    assert end == 1
    assert to_replace == "posargs"
