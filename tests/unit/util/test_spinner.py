import os
import sys
import time

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
def test_spinner_progress(capfd, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with spinner.Spinner() as spin:
        for _ in range(len(spin.frames)):
            spin.stream.write("\n")
            time.sleep(spin.refresh_rate)

    out, err = capfd.readouterr()
    assert not err
    assert len({i.strip() for i in out.split("[0]")}) > len(spin.frames) / 2


@freeze_time("2012-01-14")
def test_spinner_atty(capfd, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    with spinner.Spinner(refresh_rate=100) as spin:
        spin.stream.write("\n")
    out, err = capfd.readouterr()
    lines = out.split("\n")
    posix = os.name == "posix"
    expected = [
        "{}\r{}\r{} [0] ".format("\x1b[?25l" if posix else "", spin.CLEAR_LINE, spin.frames[0]),
        "\r\x1b[K{}".format("\x1b[?25h" if posix else ""),
    ]
    assert lines == expected


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
    expected = [
        "\r{}✔ OK ok in 0.0 second".format(spin.CLEAR_LINE),
        "\r{}✖ FAIL fail in 0.0 second".format(spin.CLEAR_LINE),
        "\r{}⚠ SKIP skip in 0.0 second".format(spin.CLEAR_LINE),
        "\r{}".format(spin.CLEAR_LINE),
    ]
    assert lines == expected
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
    expected = [
        "\r{}\r{} [2] {} | {}...".format(spin.CLEAR_LINE, spin.frames[1], "a" * 60, "b" * 49),
        "\r{}".format(spin.CLEAR_LINE),
    ]
    lines = out.split("\n")
    del lines[0]
    assert lines == expected
