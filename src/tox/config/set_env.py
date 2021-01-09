from typing import Callable, Dict, Iterator, List, Mapping, Optional

from tox.config.loader.str_convert import StrConvert


class SetEnv:
    def __init__(self, raw: str) -> None:
        self.replacer: Callable[[str, List[str]], str] = lambda s, c: s
        self._raw: Dict[str, str] = {k: v for k, v in StrConvert().to_dict(raw, (str, str))}
        self._materialized: Dict[str, str] = {}

    def load(self, item: str, chain: Optional[List[str]] = None) -> str:
        if chain is None:
            chain = [f"env:{item}"]
        if item in self._materialized:
            return self._materialized[item]
        raw = self._raw[item]
        result = self.replacer(raw, chain)  # apply any replace options
        self._materialized[item] = result
        del self._raw[item]
        return result

    def __contains__(self, item: object) -> bool:
        return item in self._materialized or item in self._raw

    def __iter__(self) -> Iterator[str]:
        # start with the materialized ones, maybe we don't need to materialize the raw ones
        yield from self._materialized.keys()
        yield from list(self._raw.keys())  # iterating over this may trigger materialization and change the dict

    def update(self, param: Mapping[str, str]) -> None:
        self._materialized.update(param)


__all__ = ("SetEnv",)
