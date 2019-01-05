import sys

from freezegun import freeze_time

from tox.util import spinner


@freeze_time("2012-01-14")
def test_spinner(capfd, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with spinner.Spinner() as spin:
        for i in range(len(spin.frames) + 1):
            spin.render_frame()
            spin.stream.write("\n")
        spin.stream.write("\n")
    out, err = capfd.readouterr()
    lines = out.split("\n")
    expected = ["\r{}\r{} [0] ".format(spin.CLEAR_LINE, i) for i in spin.frames] + [
        "\r{}\r{} [0] ".format(spin.CLEAR_LINE, spin.frames[0]),
        "",
        "\r{}".format(spin.CLEAR_LINE),
    ]
    assert lines == expected


@freeze_time("2012-01-14")
def test_spinner_atty(capfd, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    with spinner.Spinner() as spin:
        spin.stream.write("\n")
    out, err = capfd.readouterr()
    lines = out.split("\n")
    assert lines == ["\x1b[?25l", "\r\x1b[K\x1b[?25h"]


@freeze_time("2012-01-14")
def test_spinner_report(capfd, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    with spinner.Spinner() as spin:
        spin.add("ok")
        spin.add("fail")
        spin.add("skip")
        spin.succeed("ok")
        spin.fail("fail")
        spin.skip("skip")
    out, err = capfd.readouterr()
    lines = out.split("\n")
    clear = spinner.Spinner.CLEAR_LINE
    assert lines == [
        "\r{}✔ OK ok in 0.0 second".format(clear),
        "\r{}✖ FAIL fail in 0.0 second".format(clear),
        "\r{}⚠ SKIP skip in 0.0 second".format(clear),
        "\r{}".format(clear),
    ]
    assert not err


def test_spinner_long_text(capfd, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)

    with spinner.Spinner() as spin:
        spin.add("a" * 60)
        spin.add("b" * 60)
        spin.render_frame()
        sys.stdout.write("\n")
    out, err = capfd.readouterr()
    assert not err
    expected = "\r{0}\r{1} [2] {2} | {3}...\n\r{0}".format(
        spinner.Spinner.CLEAR_LINE, spinner.Spinner.frames[0], "a" * 60, "b" * 49
    )
    assert out == expected
