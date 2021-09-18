from pathlib import Path
from typing import Callable, Dict, Iterator, List, Mapping, Optional, Tuple

from tox.config.loader.api import ConfigLoadArgs
from tox.tox_env.errors import Fail

Replacer = Callable[[str, ConfigLoadArgs], str]


class SetEnv:
    def __init__(self, raw: str, name: str, env_name: Optional[str], root: Path) -> None:
        self.changed = False
        self._materialized: Dict[str, str] = {}  # env vars we already loaded
        self._raw: Dict[str, str] = {}  # could still need replacement
        self._needs_replacement: List[str] = []  # env vars that need replacement
        self._env_files: List[str] = []
        self._replacer: Replacer = lambda s, c: s
        self._name, self._env_name, self._root = name, env_name, root
        from .loader.ini.replace import find_replace_part

        for line in raw.splitlines():
            if line.strip():
                if line.startswith("file|"):
                    self._env_files.append(line[len("file|") :])
                else:
                    try:
                        key, value = self._extract_key_value(line)
                        if "{" in key:
                            raise ValueError(f"invalid line {line!r} in set_env")
                    except ValueError:
                        _, __, match = find_replace_part(line, 0)
                        if match:
                            self._needs_replacement.append(line)
                        else:
                            raise
                    else:
                        self._raw[key] = value

    def use_replacer(self, value: Replacer, args: ConfigLoadArgs) -> None:
        self._replacer = value
        for filename in self._env_files:
            self._read_env_file(filename, args)

    def _read_env_file(self, filename: str, args: ConfigLoadArgs) -> None:
        # Our rules in the documentation, some upstream environment file rules (we follow mostly the docker one):
        # - https://www.npmjs.com/package/dotenv#rules
        # - https://docs.docker.com/compose/env-file/
        env_file = Path(self._replacer(filename, args.copy()))  # apply any replace options
        env_file = env_file if env_file.is_absolute() else self._root / env_file
        if not env_file.exists():
            raise Fail(f"{env_file} does not exist for set_env")
        for env_line in env_file.read_text().splitlines():
            env_line = env_line.strip()
            if not env_line or env_line.startswith("#"):
                continue
            key, value = self._extract_key_value(env_line)
            self._raw[key] = value

    @staticmethod
    def _extract_key_value(line: str) -> Tuple[str, str]:
        key, sep, value = line.partition("=")
        if sep:
            return key.strip(), value.strip()
        else:
            raise ValueError(f"invalid line {line!r} in set_env")

    def load(self, item: str, args: Optional[ConfigLoadArgs] = None) -> str:
        if item in self._materialized:
            return self._materialized[item]
        raw = self._raw[item]
        args = ConfigLoadArgs([], self._name, self._env_name) if args is None else args
        args.chain.append(f"env:{item}")
        result = self._replacer(raw, args)  # apply any replace options
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
        while self._needs_replacement:
            line = self._needs_replacement.pop(0)
            expanded_line = self._replacer(line, ConfigLoadArgs([], self._name, self._env_name))
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
