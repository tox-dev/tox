import re
from argparse import ArgumentParser
from pathlib import Path
from typing import List, Optional, Tuple

from .req.args import build_parser
from .req.file import ReqFileLines, RequirementsFile


class PythonDeps(RequirementsFile):
    def __init__(self, raw: str, root: Path):
        super().__init__(root / "tox.ini", constraint=False)
        self._raw = self._normalize_raw(raw)
        self._unroll: Optional[Tuple[List[str], List[str]]] = None

    def _get_file_content(self, url: str) -> str:
        if self._is_url_self(url):
            return self._raw
        return super()._get_file_content(url)

    def _is_url_self(self, url: str) -> bool:
        return url == str(self._path)

    def _pre_process(self, content: str) -> ReqFileLines:
        for at, line in super()._pre_process(content):
            if line.startswith("-r") or line.startswith("-c") and line[2].isalpha():
                line = f"{line[0:2]} {line[2:]}"
            yield at, line

    @property
    def _parser(self) -> ArgumentParser:
        if self._parser_private is None:
            self._parser_private = build_parser(cli_only=True)  # e.g. no --hash for cli only
        return self._parser_private

    def lines(self) -> List[str]:
        return self._raw.splitlines()

    @staticmethod
    def _normalize_raw(raw: str) -> str:
        # a line ending in an unescaped \ is treated as a line continuation and the newline following it is effectively
        # ignored
        raw = "".join(raw.replace("\r", "").split("\\\n"))
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

    def unroll(self) -> Tuple[List[str], List[str]]:
        if self._unroll is None:
            opts_dict = vars(self.options)
            if not self.requirements and opts_dict:
                raise ValueError("no dependencies")
            result_opts: List[str] = [f"{key}={value}" for key, value in opts_dict.items()]
            result_req = [str(req) for req in self.requirements]
            self._unroll = result_opts, result_req
        return self._unroll


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

__all__ = (
    "PythonDeps",
    "ONE_ARG",
)
