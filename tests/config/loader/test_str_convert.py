import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union

import pytest

from tox.config.loader.str_convert import StrConvert
from tox.config.types import Command, EnvList

if sys.version_info >= (3, 8):  # pragma: no cover (py38+)
    from typing import Literal
else:  # pragma: no cover (py38+)
    from typing_extensions import Literal  # noqa


@pytest.mark.parametrize(
    ["raw", "value", "of_type"],
    [
        ("true", True, bool),
        ("false", False, bool),
        ("True", True, bool),
        ("False", False, bool),
        ("TruE", True, bool),
        ("FalsE", False, bool),
        ("1", True, bool),
        ("0", False, bool),
        ("1", 1, int),
        ("0", 0, int),
        ("+1", 1, int),
        ("-1", -1, int),
        ("1.1", 1.1, float),
        ("0.1", 0.1, float),
        ("+1.1", 1.1, float),
        ("-1.1", -1.1, float),
        ("magic", "magic", str),
        ("1", {"1"}, Set[str]),
        ("1", [1], List[int]),
        ("1=2", {1: 2}, Dict[int, int]),
        ("a=1\n\nc=2", {"a": 1, "c": 2}, Dict[str, int]),
        ("a", Path("a"), Path),
        ("a", Command(["a"]), Command),
        ("a,b", EnvList(["a", "b"]), EnvList),
        ("", None, Optional[int]),
        ("1", 1, Optional[int]),
        ("", None, Optional[str]),
        ("1", "1", Optional[str]),
        ("", None, Optional[List[str]]),
        ("1,2", ["1", "2"], Optional[List[str]]),
        ("1", "1", Literal["1", "2"]),
    ],
)
def test_str_convert_ok(raw: str, value: Any, of_type: Type[Any]) -> None:
    result = StrConvert().to(raw, of_type)  # noqa
    assert result == value


@pytest.mark.parametrize(
    ["raw", "of_type", "exc_type", "msg"],
    [
        ("a", TypeVar, TypeError, r"a cannot cast to .*typing.TypeVar.*"),
        ("3", Literal["1", "2"], ValueError, r"3 must be one of \('1', '2'\)"),
        ("3", Union[str, int], TypeError, r"3 cannot cast to typing.Union\[str, int\]"),
    ],
)
def test_str_convert_nok(raw: str, of_type: Type[Any], msg: str, exc_type: Type[Exception]) -> None:
    with pytest.raises(exc_type, match=msg):
        result = StrConvert().to(raw, of_type)  # noqa
