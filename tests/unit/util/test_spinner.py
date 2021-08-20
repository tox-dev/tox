# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import datetime
import os
import sys
import time

import pytest
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
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with spinner.Spinner(refresh_rate=100) as spin:
        spin.stream.write(os.linesep)
        spin.add("ok")
        spin.add("fail")
        spin.add("skip")
        spin.succeed("ok")
        spin.fail("fail")
        spin.skip("skip")
    out, err = capfd.readouterr()
    lines = out.split(os.linesep)
    del lines[0]
    expected = [
        "\r{}✔ OK ok in 0.0 seconds".format(spin.CLEAR_LINE),
        "\r{}✖ FAIL fail in 0.0 seconds".format(spin.CLEAR_LINE),
        "\r{}⚠ SKIP skip in 0.0 seconds".format(spin.CLEAR_LINE),
        "\r{}".format(spin.CLEAR_LINE),
    ]
    assert lines == expected
    assert not err


def test_spinner_long_text(capfd, monkeypatch):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    with spinner.Spinner(refresh_rate=100) as spin:
        spin.stream.write("\n")
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


def test_spinner_stdout_not_unicode(mocker, capfd):
    stdout = mocker.patch("tox.util.spinner.sys.stdout")
    stdout.encoding = "ascii"
    with spinner.Spinner(refresh_rate=100) as spin:
        for _ in range(len(spin.frames)):
            spin.render_frame()
    out, err = capfd.readouterr()
    assert not err
    assert not out
    written = "".join({i[0][0] for i in stdout.write.call_args_list})
    assert all(f in written for f in spin.frames)


@freeze_time("2012-01-14")
def test_spinner_report_not_unicode(mocker, capfd):
    stdout = mocker.patch("tox.util.spinner.sys.stdout")
    stdout.encoding = "ascii"
    # Disable color to simplify parsing output strings
    stdout.isatty = lambda: False
    with spinner.Spinner(refresh_rate=100) as spin:
        spin.stream.write(os.linesep)
        spin.add("ok!")
        spin.add("fail!")
        spin.add("skip!")
        spin.succeed("ok!")
        spin.fail("fail!")
        spin.skip("skip!")
    lines = "".join(args[0] for args, _ in stdout.write.call_args_list).split(os.linesep)
    del lines[0]
    expected = [
        "\r{}[ OK ] ok! in 0.0 seconds".format(spin.CLEAR_LINE),
        "\r{}[FAIL] fail! in 0.0 seconds".format(spin.CLEAR_LINE),
        "\r{}[SKIP] skip! in 0.0 seconds".format(spin.CLEAR_LINE),
        "\r{}".format(spin.CLEAR_LINE),
    ]
    assert lines == expected


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "0.0 seconds"),
        (1.0, "1.0 second"),
        (4.0, "4.0 seconds"),
        (4.130, "4.13 seconds"),
        (4.137, "4.137 seconds"),
        (42.12345, "42.123 seconds"),
        (61, "1 minute, 1.0 second"),
    ],
)
def test_td_human_readable(seconds, expected):
    dt = datetime.timedelta(seconds=seconds)
    assert spinner.td_human_readable(dt) == expected
