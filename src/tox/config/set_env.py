from typing import Callable, Dict, Iterator, List, Mapping, Optional, Tuple

Replacer = Callable[[str, List[str]], str]


class SetEnv:
    def __init__(self, raw: str) -> None:
        self.replacer: Replacer = lambda s, c: s
        lines = raw.splitlines()
        self._later: List[str] = []
        self._raw: Dict[str, str] = {}
        from .loader.ini.replace import find_replace_part

        for line in lines:
            if line.strip():
                try:
                    key, value = self._extract_key_value(line)
                    if "{" in key:
                        raise ValueError(f"invalid line {line!r} in set_env")
                except ValueError:
                    _, __, match = find_replace_part(line, 0, 0)
                    if match:
                        self._later.append(line)
                    else:
                        raise
                else:
                    self._raw[key] = value
        self._materialized: Dict[str, str] = {}

    @staticmethod
    def _extract_key_value(line: str) -> Tuple[str, str]:
        try:
            at = line.index("=")
        except ValueError:
            raise ValueError(f"invalid line {line!r} in set_env")
        key, value = line[:at], line[at + 1 :]
        return key.strip(), value.strip()

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
        return isinstance(item, str) and item in self.__iter__()

    def __iter__(self) -> Iterator[str]:
        # start with the materialized ones, maybe we don't need to materialize the raw ones
        yield from self._materialized.keys()
        yield from list(self._raw.keys())  # iterating over this may trigger materialization and change the dict
        while self._later:
            line = self._later.pop(0)
            expanded_line = self.replacer(line, [])
            sub_raw = {}
            for sub_line in expanded_line.splitlines():
                key, value = self._extract_key_value(sub_line)
                sub_raw[key] = value
            self._raw.update(sub_raw)
            yield from sub_raw.keys()

    def update(self, param: Mapping[str, str]) -> None:
        self._materialized.update(param)


__all__ = ("SetEnv",)
