import sys

from freezegun import freeze_time

from tox.util import spinner


@freeze_time("2012-01-14")
def test_spinner(capfd, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with spinner.Spinner(refresh_rate=100) as spin:
        for _ in range(len(spin.frames)):
            spin.stream.write("\n")
            spin.render_frame()
        spin.stream.write("\n")
    out, err = capfd.readouterr()
    lines = out.split("\n")
    expected = ["\r{}\r{} [0] ".format(spin.CLEAR_LINE, i) for i in spin.frames] + [
        "\r{}\r{} [0] ".format(spin.CLEAR_LINE, spin.frames[0]),
        "\r{}".format(spin.CLEAR_LINE),
    ]
    assert lines == expected


@freeze_time("2012-01-14")
def test_spinner_atty(capfd, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    with spinner.Spinner(refresh_rate=100) as spin:
        spin.stream.write("\n")
    out, err = capfd.readouterr()
    lines = out.split("\n")
    assert lines == [
        "\x1b[?25l\r{}\r{} [0] ".format(spin.CLEAR_LINE, spin.frames[0]),
        "\r\x1b[K\x1b[?25h",
    ]


@freeze_time("2012-01-14")
def test_spinner_report(capfd, monkeypatch):
    with spinner.Spinner(refresh_rate=100) as spin:
        monkeypatch.setattr(spin.stream, "isatty", lambda: False)
        spin.stream.write("\n")
        spin.add("ok")
        spin.add("fail")
        spin.add("skip")
        spin.succeed("ok")
        spin.fail("fail")
        spin.skip("skip")
    out, err = capfd.readouterr()
    lines = out.split("\n")
    del lines[0]
    assert lines == [
        "\r{}✔ OK ok in 0.0 second".format(spin.CLEAR_LINE),
        "\r{}✖ FAIL fail in 0.0 second".format(spin.CLEAR_LINE),
        "\r{}⚠ SKIP skip in 0.0 second".format(spin.CLEAR_LINE),
        "\r{}".format(spin.CLEAR_LINE),
    ]
    assert not err


def test_spinner_long_text(capfd, monkeypatch):
    with spinner.Spinner(refresh_rate=100) as spin:
        spin.stream.write("\n")
        monkeypatch.setattr(spin.stream, "isatty", lambda: False)
        spin.add("a" * 60)
        spin.add("b" * 60)
        spin.render_frame()
        spin.stream.write("\n")
    out, err = capfd.readouterr()
    assert not err
    expected = "\r{}\r{} [2] {} | {}...".format(
        spin.CLEAR_LINE, spin.frames[1], "a" * 60, "b" * 49
    )
    lines = out.split("\n")
    del lines[0]
    assert lines == [expected, "\r{}".format(spin.CLEAR_LINE)]
