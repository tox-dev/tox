from tox.util.stdlib import suppress_output


def test_suppress_output_non_ascii():
    # https://github.com/tox-dev/tox/issues/1908
    with suppress_output():
        print("こんにちは世界")
