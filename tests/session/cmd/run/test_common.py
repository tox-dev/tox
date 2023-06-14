from __future__ import annotations

import os
import re
from argparse import ArgumentError, ArgumentParser, Namespace
from typing import TYPE_CHECKING

import pytest

from tox.session.cmd.run.common import InstallPackageAction, SkipMissingInterpreterAction

if TYPE_CHECKING:
    from pathlib import Path

    from tox.pytest import ToxProjectCreator


@pytest.mark.parametrize("values", ["config", None, "true", "false"])
def test_skip_missing_interpreter_action_ok(values: str | None) -> None:
    args_namespace = Namespace()
    SkipMissingInterpreterAction(option_strings=["-i"], dest="into")(ArgumentParser(), args_namespace, values)
    expected = "true" if values is None else values
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
    proj = tox_project({"tox.ini": ""})
    outcome = proj.run("exec", "-qq", "--", "python", "-c", "print('foo')")

    outcome.assert_success()
    outcome.assert_out_err(f"foo{os.linesep}", "")
