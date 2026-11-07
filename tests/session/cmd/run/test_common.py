from __future__ import annotations

import os
import re
import sys
from argparse import ArgumentError, ArgumentParser, Namespace
from typing import TYPE_CHECKING, Final
from urllib.parse import quote

import pytest

from tox.session.cmd.run.common import InstallPackageAction, SkipMissingInterpreterAction

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        pytest.param("config", "config", id="config"),
        pytest.param(None, "true", id="none"),
        pytest.param("true", "true", id="true"),
        pytest.param("false", "false", id="false"),
    ],
)
def test_skip_missing_interpreter_action_ok(values: str | None, expected: str) -> None:
    args_namespace = Namespace()
    SkipMissingInterpreterAction(option_strings=["-i"], dest="into")(ArgumentParser(), args_namespace, values)
    assert args_namespace.into == expected


def test_skip_missing_interpreter_action_nok() -> None:
    argument_parser = ArgumentParser()
    with pytest.raises(ArgumentError, match=r"value must be 'config', 'true', or 'false' \(got 'bad value'\)"):
        SkipMissingInterpreterAction(option_strings=["-i"], dest="into")(argument_parser, Namespace(), "bad value")


def test_install_pkg_ok(tmp_path: Path) -> None:
    argument_parser = ArgumentParser()
    path = tmp_path / "a"
    path.write_text("")
    namespace = Namespace()
    InstallPackageAction(option_strings=["--install-pkg"], dest="into")(argument_parser, namespace, str(path))
    assert namespace.into == path


def test_install_pkg_file_uri(tmp_path: Path) -> None:
    argument_parser = ArgumentParser()
    path = tmp_path / "pkg.whl"
    path.write_text("")
    uri = path.as_uri()
    namespace = Namespace()
    InstallPackageAction(option_strings=["--install-pkg"], dest="into")(argument_parser, namespace, uri)
    assert namespace.into == path


@pytest.mark.skipif(sys.platform == "win32", reason="posix file uri")
def test_install_pkg_file_uri_percent_encoded_posix(tmp_path: Path) -> None:
    argument_parser = ArgumentParser()
    path = tmp_path / "pkg+extra-1.0.whl"
    path.write_text("")
    # Build a file: URI with percent-encoded '+' in the filename
    uri = "file://" + quote(str(path), safe="/")
    namespace = Namespace()
    InstallPackageAction(option_strings=["--install-pkg"], dest="into")(argument_parser, namespace, uri)
    assert namespace.into == path


@pytest.mark.skipif(sys.platform != "win32", reason="windows file uri")
def test_install_pkg_file_uri_percent_encoded_windows(tmp_path: Path) -> None:
    argument_parser = ArgumentParser()
    path = tmp_path / "pkg+extra-1.0.whl"
    path.write_text("")
    # Build a file: URI with percent-encoded '+' in the filename
    uri = "file:///" + quote(str(path).replace("\\", "/"), safe=":/")
    namespace = Namespace()
    InstallPackageAction(option_strings=["--install-pkg"], dest="into")(argument_parser, namespace, uri)
    assert namespace.into == path


def test_install_pkg_file_uri_decoded_once(tmp_path: Path) -> None:
    directory: Final[Path] = tmp_path / "feature%2Flogin"
    directory.mkdir()
    path: Final[Path] = directory / "pkg-1.0.whl"
    path.write_text("")
    uri: Final[str] = path.as_uri()
    assert "%252F" in uri
    namespace: Final[Namespace] = Namespace()
    InstallPackageAction(option_strings=["--install-pkg"], dest="into")(ArgumentParser(), namespace, uri)
    assert namespace.into == path


def test_install_pkg_file_uri_does_not_exist(tmp_path: Path) -> None:
    argument_parser = ArgumentParser()
    path = tmp_path / "missing.whl"
    uri = path.as_uri()
    with pytest.raises(ArgumentError, match=re.escape(f"{path} does not exist")):
        InstallPackageAction(option_strings=["--install-pkg"], dest="into")(argument_parser, Namespace(), uri)


def test_install_pkg_does_not_exist(tmp_path: Path) -> None:
    argument_parser = ArgumentParser()
    path = str(tmp_path / "a")
    with pytest.raises(ArgumentError, match=re.escape(f"argument --install-pkg: {path} does not exist")):
        InstallPackageAction(option_strings=["--install-pkg"], dest="into")(argument_parser, Namespace(), path)


def test_install_pkg_not_file(tmp_path: Path) -> None:
    argument_parser = ArgumentParser()
    path = str(tmp_path)
    with pytest.raises(ArgumentError, match=re.escape(f"argument --install-pkg: {path} is not a file")):
        InstallPackageAction(option_strings=["--install-pkg"], dest="into")(argument_parser, Namespace(), path)


def test_install_pkg_empty() -> None:
    argument_parser = ArgumentParser()
    with pytest.raises(ArgumentError, match=re.escape("argument --install-pkg: cannot be empty")):
        InstallPackageAction(option_strings=["--install-pkg"], dest="into")(argument_parser, Namespace(), "")


def test_empty_report(tox_project: ToxProjectCreator) -> None:
    outcome = tox_project({"tox.ini": ""}).run("exec", "-qq", "--", "python", "-c", "print('foo')")

    outcome.assert_success()
    outcome.assert_out_err(f"foo{os.linesep}", "")
