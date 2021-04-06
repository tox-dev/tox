import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

from packaging.requirements import InvalidRequirement, Requirement

LOGGER = logging.getLogger(__name__)


VCS = ["ftp", "ssh", "git", "hg", "bzr", "sftp", "svn"]
VALID_SCHEMAS = ["http", "https", "file"] + VCS


def is_url(name: str) -> bool:
    return get_url_scheme(name) in VALID_SCHEMAS


def get_url_scheme(url: str) -> Optional[str]:
    return None if ":" not in url else url.partition(":")[0].lower()


NO_ARG = {
    "--no-index",
    "--prefer-binary",
    "--require-hashes",
    "--pre",
}
ONE_ARG = {
    "-i",
    "--index-url",
    "--extra-index-url",
    "-e",
    "--editable",
    "-c",
    "--constraint",
    "-r",
    "--requirement",
    "-f",
    "--find-links",
    "--trusted-host",
    "--use-feature",
    "--no-binary",
    "--only-binary",
}
ONE_ARG_ESCAPE = {
    "-c",
    "--constraint",
    "-r",
    "--requirement",
    "-f",
    "--find-links",
    "-e",
    "--editable",
}


class PipRequirementEntry(ABC):
    @abstractmethod
    def as_args(self) -> Iterable[str]:
        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other: Any) -> bool:  # noqa: U100
        raise NotImplementedError

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    @abstractmethod
    def __str__(self) -> str:
        raise NotImplementedError


class Flags(PipRequirementEntry):
    def __init__(self, *args: str) -> None:
        self.args: Iterable[str] = args

    def as_args(self) -> Iterable[str]:
        return self.args

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Flags) and self.args == other.args

    def __str__(self) -> str:
        return " ".join(self.args)


class RequirementWithFlags(Requirement, Flags):
    def __init__(self, requirement_string: str, args: Sequence[str]) -> None:
        Requirement.__init__(self, requirement_string)
        Flags.__init__(self, *args)

    def as_args(self) -> Iterable[str]:
        return (Requirement.__str__(self), *self.args)

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, RequirementWithFlags)
            and self.args == other.args
            and Requirement.__str__(self) == Requirement.__str__(other)
        )

    def __str__(self) -> str:
        return " ".join((Requirement.__str__(self), *self.args))


class PathReq(PipRequirementEntry):
    def __init__(self, path: Path, extras: List[str]) -> None:
        self.path = path
        self.extras = extras

    def as_args(self) -> Iterable[str]:
        return (str(self),)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.path == other.path and self.extras == other.extras

    def __str__(self) -> str:
        extra_group = f"[{','.join(self.extras)}]" if self.extras else ""
        return f"{self.path}{extra_group}"


class EditablePathReq(PathReq):
    def as_args(self) -> Iterable[str]:
        return ("-e", super().__str__())

    def __str__(self) -> str:
        return f"-e {super().__str__()}"


class UrlReq(PipRequirementEntry):
    def __init__(self, url: str) -> None:
        self.url = url

    def as_args(self) -> Iterable[str]:
        return (self.url,)

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, UrlReq) and self.url == other.url

    def __str__(self) -> str:
        return self.url


# https://www.python.org/dev/peps/pep-0508/#extras
_EXTRA_PATH = re.compile(r"(.*)\[([-._,\sa-zA-Z0-9]*)]")
_EXTRA_ELEMENT = re.compile(r"[a-zA-Z0-9]*[-._a-zA-Z0-9]")


class PythonDeps:
    """A sub-set form of the requirements files (support tox 3 syntax, and --hash is not valid on CLI)"""

    def __init__(self, raw: str, root: Optional[Path] = None):
        self._root = Path().cwd() if root is None else root.resolve()
        self._raw = raw
        self._result: Optional[List[Any]] = None

    def validate_and_expand(self) -> List[Any]:
        if self._result is None:
            raw = self._normalize_raw()
            result: List[Any] = []
            ini_dir = self.root
            for at, line in enumerate(raw.splitlines(), start=1):
                line = re.sub(r"(?<!\\)\s#.*", "", line).strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("-"):
                    self._expand_flag(ini_dir, line, result)
                else:
                    self._expand_non_flag(at, ini_dir, line, result)
            self._result = result
        return self._result

    def _normalize_raw(self) -> str:
        # a line ending in an unescaped \ is treated as a line continuation and the newline following it is effectively
        # ignored
        raw = "".join(self._raw.replace("\r", "").split("\\\n"))
        lines: List[str] = []
        for line in raw.splitlines():
            # for tox<4 supporting requirement/constraint files via -rreq.txt/-creq.txt
            arg_match = next(
                (
                    arg
                    for arg in ONE_ARG
                    if line.startswith(arg)
                    and len(line) > len(arg)
                    and not (line[len(arg)].isspace() or line[len(arg)] == "=")
                ),
                None,
            )
            if arg_match is not None:
                line = f"{arg_match} {line[len(arg_match):]}"
            # escape spaces
            escape_match = next((e for e in ONE_ARG_ESCAPE if line.startswith(e) and line[len(e)].isspace()), None)
            if escape_match is not None:
                # escape not already escaped spaces
                escaped = re.sub(r"(?<!\\)(\s)", r"\\\1", line[len(escape_match) + 1 :])
                line = f"{line[:len(escape_match)]} {escaped}"
            lines.append(line)
        adjusted = "\n".join(lines)
        raw = f"{adjusted}\n" if raw.endswith("\\\n") else adjusted  # preserve trailing newline if input has it
        return raw

    def __str__(self) -> str:
        return self._raw

    @property
    def root(self) -> Path:
        return self._root

    def _expand_non_flag(self, at: int, ini_dir: Path, line: str, result: List[Any]) -> None:  # noqa
        requirement, extra = self._load_requirement_with_extra(line)
        try:
            if not extra:
                req = Requirement(requirement)
            else:
                req = RequirementWithFlags(requirement, extra)
        except InvalidRequirement as exc:
            if is_url(line) or any(line.startswith(f"{v}+") and is_url(line[len(v) + 1 :]) for v in VCS):
                result.append(UrlReq(line))
            else:
                for path, extra in self._path_candidate(ini_dir / line):
                    try:
                        if path.exists() and (path.is_file() or path.is_dir()):
                            result.append(PathReq(path, extra))
                            break
                    except OSError:  # https://bugs.python.org/issue42855 # pragma: no cover
                        continue
                else:
                    raise ValueError(f"{at}: {line}") from exc
        else:
            result.append(req)

    @staticmethod
    def _path_candidate(path: Path) -> Iterator[Tuple[Path, List[str]]]:
        yield path, []
        # if there's a trailing [a,b] section that could mean either a folder or extras, try both
        match = _EXTRA_PATH.fullmatch(path.name)
        if match:
            extras = []
            for extra in match.group(2).split(","):
                extra = extra.strip()
                if not extra:
                    continue
                if not _EXTRA_ELEMENT.fullmatch(extra):
                    break
                extras.append(extra)
            else:
                yield path.parent / match.group(1), extras

    def _load_requirement_with_extra(self, line: str) -> Tuple[str, List[str]]:
        return line, []

    def _expand_flag(self, ini_dir: Path, line: str, result: List[Any]) -> None:
        words = list(re.split(r"(?<!\\)(\s|=)", line, maxsplit=1))
        first = words[0]
        if first in NO_ARG:
            if len(words) != 1:  # argument provided
                raise ValueError(line)
            result.append(Flags(first))
        elif first in ONE_ARG:
            if len(words) != 3:  # no argument provided
                raise ValueError(line)
            if len(re.split(r"(?<!\\)\s", words[2])) > 1:  # too many arguments provided
                raise ValueError(line)
            if first in ("-r", "--requirement", "-c", "--constraint"):
                raw_path = line[len(first) + 1 :].strip()
                unescaped_path = re.sub(r"\\(\s)", r"\1", raw_path)
                path = Path(unescaped_path)
                if not path.is_absolute():
                    path = ini_dir / path
                if not path.exists():
                    raise ValueError(f"requirement file path {str(path)!r} does not exist")
                of_type = RequirementsFile if first in ("-r", "--requirement") else ConstraintFile
                req_file = of_type(path, root=self.root)
                req_file.validate_and_expand()
                result.append(req_file)
            elif first in ("-e", "--editable"):
                result.append(EditablePathReq(Path(words[2]), []))
            elif first in [
                "-i",
                "--index-url",
                "--extra-index-url",
                "-f",
                "--find-links",
                "--trusted-host",
                "--use-feature",
                "--no-binary",
                "--only-binary",
            ]:
                result.append(Flags(first, words[2]))
            else:
                raise ValueError(first)
        else:
            raise ValueError(line)

    def unroll(self) -> List[Union[Dict[str, Any], str]]:
        into: List[Union[Dict[str, Any], str]] = []
        for element in self.validate_and_expand():
            if isinstance(element, (RequirementsFile, ConstraintFile)):
                res: Union[Dict[str, Any], str] = {str(element): element.unroll()}
            elif isinstance(element, (Requirement, Flags, PathReq, EditablePathReq, UrlReq)):
                res = str(element)
            else:  # pragma: no cover
                raise ValueError(element)  # pragma: no cover
            into.append(res)
        return into


class _BaseRequirementsFile(PythonDeps, PipRequirementEntry):
    """
    Specification is defined within pip itself and documented under:
    - https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format
    - https://github.com/pypa/pip/blob/master/src/pip/_internal/req/constructors.py#L291
    """

    arg_flag: str = ""

    def __init__(self, path: Path, root: Path):
        self.path = path
        super().__init__(path.read_text(), root=root)

    def __str__(self) -> str:
        return f"{self.arg_flag} {self.rel_path}"

    def as_args(self) -> Iterable[str]:
        return self.arg_flag, str(self.rel_path)

    @property
    def rel_path(self) -> Path:
        try:
            return self.path.relative_to(self.root)
        except ValueError:
            return self.path

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.path == other.path

    def _normalize_raw(self) -> str:
        # a line ending in an unescaped \ is treated as a line continuation and the newline following it is effectively
        # ignored
        raw = "".join(self._raw.replace("\r", "").split("\\\n"))
        # Since version 10, pip supports the use of environment variables inside the requirements file.
        # You can now store sensitive data (tokens, keys, etc.) in environment variables and only specify the variable
        # name for your requirements, letting pip lookup the value at runtime.
        # You have to use the POSIX format for variable names including brackets around the uppercase name as shown in
        # this example: ${API_TOKEN}. pip will attempt to find the corresponding environment variable defined on the
        # host system at runtime.
        while True:
            match = re.search(r"\$\{([A-Z_]+)\}", raw)
            if match is None:
                break
            value = os.environ.get(match.groups()[0], "")
            start, end = match.span()
            raw = f"{raw[:start]}{value}{raw[end:]}"
        return raw


_HASH = re.compile(r"\B--hash(=|\s+)sha(256:[a-z0-9]{64}|384:[a-z0-9]{96}|521:[a-z0-9]{128})\b")


class RequirementsFile(_BaseRequirementsFile):
    arg_flag = "-r"

    def _load_requirement_with_extra(self, line: str) -> Tuple[str, List[str]]:
        args = [f"--hash=sha{i[1]}" for i in _HASH.findall(line)]
        value = _HASH.sub("", line).strip()
        return value, args


class ConstraintFile(_BaseRequirementsFile):
    arg_flag = "-c"


__all__ = (
    "Flags",
    "RequirementWithFlags",
    "PathReq",
    "EditablePathReq",
    "UrlReq",
    "PythonDeps",
    "RequirementsFile",
    "ConstraintFile",
    "ONE_ARG",
    "ONE_ARG_ESCAPE",
    "NO_ARG",
)
