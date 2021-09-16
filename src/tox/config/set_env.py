from typing import Callable, Dict, Iterator, List, Mapping, Optional, Tuple

from tox.config.loader.api import ConfigLoadArgs

Replacer = Callable[[str, ConfigLoadArgs], str]


class SetEnv:
    def __init__(self, raw: str, name: str, env_name: Optional[str]) -> None:
        self.replacer: Replacer = lambda s, c: s
        self._later: List[str] = []
        self._raw: Dict[str, str] = {}
        self._name, self._env_name = name, env_name
        from .loader.ini.replace import find_replace_part

        for line in raw.splitlines():
            if line.strip():
                try:
                    key, value = self._extract_key_value(line)
                    if "{" in key:
                        raise ValueError(f"invalid line {line!r} in set_env")
                except ValueError:
                    _, __, match = find_replace_part(line, 0)
                    if match:
                        self._later.append(line)
                    else:
                        raise
                else:
                    self._raw[key] = value
        self._materialized: Dict[str, str] = {}
        self.changed = False

    @staticmethod
    def _extract_key_value(line: str) -> Tuple[str, str]:
        key, sep, value = line.partition("=")
        if sep:
            return key.strip(), value.strip()
        else:
            raise ValueError(f"invalid line {line!r} in set_env")

    def load(self, item: str, args: Optional[ConfigLoadArgs] = None) -> str:
        args = ConfigLoadArgs([], self._name, self._env_name) if args is None else args
        args.chain.append(f"env:{item}")
        if item in self._materialized:
            return self._materialized[item]
        raw = self._raw[item]
        result = self.replacer(raw, args)  # apply any replace options
        result = result.replace(r"\#", "#")  # unroll escaped comment with replacement
        self._materialized[item] = result
        self._raw.pop(item, None)  # if the replace requires the env we may be called again, so allow pop to fail
        return result

    def __contains__(self, item: object) -> bool:
        return isinstance(item, str) and item in self.__iter__()

    def __iter__(self) -> Iterator[str]:
        # start with the materialized ones, maybe we don't need to materialize the raw ones
        yield from self._materialized.keys()
        yield from list(self._raw.keys())  # iterating over this may trigger materialization and change the dict
        while self._later:
            line = self._later.pop(0)
            expanded_line = self.replacer(line, ConfigLoadArgs([], self._name, self._env_name))
            sub_raw = dict(self._extract_key_value(sub_line) for sub_line in expanded_line.splitlines() if sub_line)
            self._raw.update(sub_raw)
            yield from sub_raw.keys()

    def update(self, param: Mapping[str, str], *, override: bool = True) -> None:
        for key, value in param.items():
            # do not override something already set explicitly
            if override or (key not in self._raw and key not in self._materialized):
                self._materialized[key] = value
                self.changed = True


__all__ = ("SetEnv",)
