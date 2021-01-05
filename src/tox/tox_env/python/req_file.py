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


class RequirementsFile:
    """
    Specification is defined within pip itself and documented under:
    - https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format
    - https://github.com/pypa/pip/blob/master/src/pip/_internal/req/constructors.py#L291
    """

    VALID_OPTIONS = {
        "no_arg": [
            "--no-index",
            "--prefer-binary",
            "--require-hashes",
            "--pre",
        ],
        "one_arg": [
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
        ],
    }

    def __init__(self, raw: str, allow_short_req_file: bool = True, root: Optional[Path] = None) -> None:
        self._root = Path().cwd() if root is None else root
        if allow_short_req_file:  # patch tox supporting requirements files via -rrequirements.txt
            r = ((f"-r {i[2:]}" if len(i) >= 3 and i.startswith("-r") and i[2] != " " else i) for i in raw.splitlines())
            adjusted = "\n".join(r)
            raw = f"{adjusted}\n" if raw.endswith("\\\n") else adjusted
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
            if line.startswith("#"):
                continue
            line = re.sub(r"\s#.*", "", line).strip()
            if not line:
                continue
            if line.startswith("-"):  # handle flags
                words = re.findall(r"\S+", line)
                first = words[0]
                if first in self.VALID_OPTIONS["no_arg"]:
                    if len(words) != 1:
                        raise ValueError(line)
                    else:
                        result.append(" ".join(words))
                elif first in self.VALID_OPTIONS["one_arg"]:
                    if len(words) != 2:
                        raise ValueError(line)
                    else:
                        if first == "-r":
                            path = Path(line[3:].strip())
                            if not path.is_absolute():
                                path = ini_dir / path
                            req_file = RequirementsFile(path.read_text(), allow_short_req_file=False, root=self.root)
                            result.extend(req_file.validate_and_expand())
                        else:
                            result.append(" ".join(words))
                else:
                    raise ValueError(line)
            else:
                try:
                    req = Requirement(line)
                    result.append(str(req))
                except InvalidRequirement as exc:
                    if is_url(line) or any(line.startswith(f"{v}+") and is_url(line[len(v) + 1 :]) for v in VCS):
                        result.append(line)
                    else:
                        path = ini_dir / line
                        try:
                            is_valid_file = path.exists() and path.is_file()
                        except OSError:  # https://bugs.python.org/issue42855 # pragma: no cover
                            is_valid_file = False  # pragma: no cover
                        if not is_valid_file:
                            raise ValueError(f"{at}: {line}") from exc
                        result.append(str(path))
        return result

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
