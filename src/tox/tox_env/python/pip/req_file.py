from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from packaging.requirements import Requirement

from tox.util.typing_compat import override

from .req.file import ParsedRequirement, ReqFileLines, RequirementsFile

_UNESCAPED_SPACE_RE = re.compile(
    r"""
    (?<! \\ )   # not preceded by backslash
    ( \s )      # capture whitespace
    """,
    re.VERBOSE,
)

if TYPE_CHECKING:
    import sys
    from argparse import ArgumentParser, Namespace
    from pathlib import Path
    from typing import ClassVar, Final

    if sys.version_info >= (3, 11):  # pragma: >=3.11 cover
        from typing import Self
    else:  # pragma: <3.11 cover
        from typing_extensions import Self


class _PythonRequirementsFile(RequirementsFile):
    _CONSTRAINT: ClassVar[bool]
    _FIELD: ClassVar[str]

    def __init__(self, raw: str | list[str] | list[Requirement], root: Path) -> None:
        super().__init__(root / "tox.ini", constraint=self._CONSTRAINT)
        got = raw if isinstance(raw, str) else "\n".join(str(i) for i in raw)
        self._raw = self._normalize_raw(got)
        self._unroll: tuple[list[str], list[str]] | None = None
        self._req_parser_: RequirementsFile | None = None

    @property
    @override
    def _req_parser(self) -> RequirementsFile:
        if self._req_parser_ is None:
            self._req_parser_ = RequirementsFile(path=self._path, constraint=self._CONSTRAINT)
        return self._req_parser_

    @override
    def _get_file_content(self, url: str) -> str:
        return self._raw  # only the file itself is read here, nested files go through the plain parser

    @override
    def _pre_process(self, content: str) -> ReqFileLines:
        for at, line in super()._pre_process(content):
            if line.startswith("-r") or (line.startswith("-c") and line[2:3].isalpha()):
                found_line = f"{line[0:2]} {line[2:]}"
            else:
                found_line = line
            yield at, found_line

    def lines(self) -> list[str]:
        return self._raw.splitlines()

    @classmethod
    def _normalize_raw(cls, raw: str) -> str:
        # a line ending in an unescaped \ is treated as a line continuation and the newline following it is effectively
        # ignored
        raw = "".join(raw.replace("\r", "").split("\\\n"))
        # for tox<4 supporting requirement/constraint files via -rreq.txt/-creq.txt
        lines: list[str] = [cls._normalize_line(line) for line in raw.splitlines()]
        adjusted = "\n".join(cls._adjust_lines(lines))
        return f"{adjusted}\n" if raw.endswith("\\\n") else adjusted

    @classmethod
    def _adjust_lines(cls, lines: list[str]) -> list[str]:
        return lines

    @classmethod
    def _normalize_line(cls, line: str) -> str:
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
            line = f"{arg_match} {line[len(arg_match) :]}"
        escape_match = next(
            (e for e in ONE_ARG_ESCAPE if line.startswith(e) and len(line) > len(e) and line[len(e)].isspace()), None
        )
        if escape_match is not None:
            escaped = _UNESCAPED_SPACE_RE.sub(r"\\\1", line[len(escape_match) + 1 :])
            line = f"{line[: len(escape_match)]} {escaped}"
        return line

    @override
    def _parse_requirements(self, opt: Namespace, recurse: bool) -> list[ParsedRequirement]:
        # requirements recursively included from other files are not checked
        requirements = super()._parse_requirements(opt, recurse)
        for req in requirements:
            if req.from_file == str(self.path):
                self._validate_requirement(req)
        return requirements

    def _validate_requirement(self, req: ParsedRequirement) -> None:
        raise NotImplementedError

    def unroll(self) -> tuple[list[str], list[str]]:
        if self._unroll is None:
            opts_dict = vars(self.options)
            if not self.requirements and opts_dict:
                msg = "no dependencies"
                raise ValueError(msg)
            self._unroll = _render_options(opts_dict), [str(req) for req in self.requirements]
        return self._unroll

    @classmethod
    def factory(cls, root: Path, raw: object) -> Self:
        if not (
            isinstance(raw, str)
            or (
                isinstance(raw, list)
                and (all(isinstance(i, str) for i in raw) or all(isinstance(i, Requirement) for i in raw))
            )
        ):
            raise TypeError(_factory_type_error(cls._FIELD, raw))
        return cls(cast("str | list[str] | list[Requirement]", raw), root)


class PythonDeps(_PythonRequirementsFile):
    # these options are valid in requirements.txt, but not via pip cli and
    # thus cannot be used in the testenv `deps` list
    _illegal_options: Final[list[str]] = ["hash"]
    _CONSTRAINT = False
    _FIELD = "deps"

    @override
    def _extend_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("--no-deps", action="store_true", dest="no_deps", default=False)

    @override
    def _merge_option_line(self, base_opt: Namespace, opt: Namespace, filename: str) -> None:
        super()._merge_option_line(base_opt, opt, filename)
        if getattr(opt, "no_deps", False):  # if the option comes from a requirements file this flag is missing there
            base_opt.no_deps = True

    @override
    def _option_to_args(self, opt: Namespace) -> list[str]:
        result = super()._option_to_args(opt)
        if getattr(opt, "no_deps", False):
            result.append("--no-deps")
        return result

    @override
    def _validate_requirement(self, req: ParsedRequirement) -> None:
        for illegal_option in self._illegal_options:
            if req.options.get(illegal_option):
                msg = f"Cannot use --{illegal_option} in deps list, it must be in requirements file. ({req})"
                raise ValueError(msg)

    def __iadd__(self, other: PythonDeps) -> Self:
        self._raw += "\n" + other._raw
        return self


class PythonConstraints(_PythonRequirementsFile):
    _CONSTRAINT = True
    _FIELD = "constraints"

    @classmethod
    @override
    def _adjust_lines(cls, lines: list[str]) -> list[str]:
        if any(line.startswith("-") for line in lines):
            msg = "only constraints files or URLs can be provided"
            raise ValueError(msg)
        return [f"-c {line}" for line in lines]

    @override
    def _validate_requirement(self, req: ParsedRequirement) -> None:
        if req.options:
            msg = f"Cannot provide options in constraints list, only paths or URL can be provided. ({req})"
            raise ValueError(msg)


def _factory_type_error(field: str, raw: object) -> str:
    expected = "str, list[str], or list[Requirement]"
    if isinstance(raw, list):
        bad_items = ", ".join(
            f"[{i}] {type(item).__name__}" for i, item in enumerate(raw) if not isinstance(item, (str, Requirement))
        )
        return f"{field} expected {expected}, got list with invalid items: {bad_items}"
    return f"{field} expected {expected}, got {type(raw).__name__}: {raw!r}"


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


def _render_options(options: dict[str, object]) -> list[str]:
    # set-valued options (e.g. no_binary) render sorted so the value is stable across hash seeds - the install
    # cache compares these strings and an order change would force a spurious recreate
    return [
        f"{key}={','.join(sorted(cast('set[str]', value))) if isinstance(value, set) else value}"
        for key, value in options.items()
    ]


__all__ = (
    "ONE_ARG",
    "PythonConstraints",
    "PythonDeps",
)
