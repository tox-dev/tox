from argparse import ArgumentParser, ArgumentTypeError, Namespace
from typing import Optional

import pytest

from tox.session.cmd.run.common import SkipMissingInterpreterAction


@pytest.mark.parametrize("values", ["config", None, "true", "false"])
def test_skip_missing_interpreter_action_ok(values: Optional[str]) -> None:
    args_namespace = Namespace()
    SkipMissingInterpreterAction(option_strings=["-i"], dest="into")(ArgumentParser(), args_namespace, values)
    expected = "true" if values is None else values
    assert args_namespace.into == expected


def test_skip_missing_interpreter_action_nok() -> None:
    argument_parser = ArgumentParser()
    with pytest.raises(ArgumentTypeError, match=r"value must be 'config', 'true', or 'false' \(got 'bad value'\)"):
        SkipMissingInterpreterAction(option_strings=["-i"], dest="into")(argument_parser, Namespace(), "bad value")
