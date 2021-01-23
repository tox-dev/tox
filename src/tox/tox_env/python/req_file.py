import logging
import os
import re
from contextlib import contextmanager
from pathlib import Path
from tempfile import mkstemp
from typing import Iterator, List, Optional

from packaging.requirements import InvalidRequirement, Requirement

LOGGER = logging.getLogger(__name__)


VCS = ["ftp", "ssh", "git", "hg", "bzr", "sftp", "svn"]
VALID_SCHEMAS = ["http", "https", "file"] + VCS


def is_url(name: str) -> bool:
    return get_url_scheme(name) in VALID_SCHEMAS


def get_url_scheme(url: str) -> Optional[str]:
    return None if ":" not in url else url.split(":", 1)[0].lower()


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


class RequirementsFile:
    """
    Specification is defined within pip itself and documented under:
    - https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format
    - https://github.com/pypa/pip/blob/master/src/pip/_internal/req/constructors.py#L291
    """

    def __init__(self, raw: str, within_tox_ini: bool = True, root: Optional[Path] = None) -> None:
        self._root = Path().cwd() if root is None else root.resolve()
        if within_tox_ini:  # patch the content coming from tox.ini
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
        self._raw = raw

    def __str__(self) -> str:
        return self._raw

    @property
    def root(self) -> Path:
        return self._root

    def validate_and_expand(self) -> List[str]:
        raw = self._normalize_raw()
        result: List[str] = []
        ini_dir = self.root
        for at, line in enumerate(raw.splitlines(), start=1):
            line = re.sub(r"(?<!\\)\s#.*", "", line).strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("-"):
                self._expand_flag(ini_dir, line, result)
            else:
                self._expand_non_flag(at, ini_dir, line, result)
        return result

    def _expand_non_flag(self, at: int, ini_dir: Path, line: str, result: List[str]) -> None:  # noqa
        try:
            req = Requirement(line)
        except InvalidRequirement as exc:
            if is_url(line) or any(line.startswith(f"{v}+") and is_url(line[len(v) + 1 :]) for v in VCS):
                result.append(line)
            else:
                path = ini_dir / line
                try:
                    is_valid_file = path.exists() and (path.is_file() or path.is_dir())
                except OSError:  # https://bugs.python.org/issue42855 # pragma: no cover
                    is_valid_file = False  # pragma: no cover
                if not is_valid_file:
                    raise ValueError(f"{at}: {line}") from exc
                result.append(str(path))
        else:
            result.append(str(req))

    def _expand_flag(self, ini_dir: Path, line: str, result: List[str]) -> None:
        words = [i for i in re.split(r"(?<!\\)(\s|=)", line, maxsplit=1)]
        first = words[0]
        if first in NO_ARG:
            if len(words) != 1:  # argument provided
                raise ValueError(line)
            result.append(first)
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
                req_file = RequirementsFile(path.read_text(), within_tox_ini=False, root=self.root)
                result.extend(req_file.validate_and_expand())
            else:
                result.append(f"{first} {words[2]}")
        else:
            raise ValueError(line)

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

    @contextmanager
    def with_file(self) -> Iterator[Path]:
        file_no, path = mkstemp(dir=self.root, prefix="requirements-", suffix=".txt")
        try:
            try:
                with open(path, "wt") as f:
                    f.write(self._raw)
            finally:
                os.close(file_no)
            yield Path(path)
        finally:
            os.unlink(path)


__all__ = (
    "RequirementsFile",
    "ONE_ARG",
    "ONE_ARG_ESCAPE",
    "NO_ARG",
)
