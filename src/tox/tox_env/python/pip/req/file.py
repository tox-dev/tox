"""Adapted from the pip code base"""

import os
import re
import shlex
import urllib.parse
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import IO, Any, Dict, Iterator, List, Optional, Tuple, Union
from urllib.request import urlopen

import chardet
from packaging.requirements import InvalidRequirement, Requirement

from .args import build_parser
from .util import VCS, get_url_scheme, is_url, url_to_path

# Matches environment variable-style values in '${MY_VARIABLE_1}' with the variable name consisting of only uppercase
# letters, digits or the '_' (underscore). This follows the POSIX standard defined in IEEE Std 1003.1, 2013 Edition.
_ENV_VAR_RE = re.compile(r"(?P<var>\${(?P<name>[A-Z0-9_]+)})")
_SCHEME_RE = re.compile(r"^(http|https|file):", re.I)
_COMMENT_RE = re.compile(r"(^|\s+)#.*$")
# https://www.python.org/dev/peps/pep-0508/#extras
_EXTRA_PATH = re.compile(r"(.*)\[([-._,\sa-zA-Z0-9]*)]")
_EXTRA_ELEMENT = re.compile(r"[a-zA-Z0-9]*[-._a-zA-Z0-9]")
ReqFileLines = Iterator[Tuple[int, str]]


class ParsedRequirement:
    def __init__(self, req: str, options: Dict[str, Any], from_file: str, lineno: int) -> None:
        req = req.encode("utf-8").decode("utf-8")
        try:
            self._requirement: Union[Requirement, Path, str] = Requirement(req)
        except InvalidRequirement:
            if is_url(req) or any(req.startswith(f"{v}+") and is_url(req[len(v) + 1 :]) for v in VCS):
                self._requirement = req
            else:
                root = Path(from_file).parent
                extras: List[str] = []
                match = _EXTRA_PATH.fullmatch(Path(req).name)
                if match:
                    for extra in match.group(2).split(","):
                        extra = extra.strip()
                        if not extra:
                            continue
                        if not _EXTRA_ELEMENT.fullmatch(extra):
                            extras = []
                            path = root / req
                            break
                        extras.append(extra)
                    else:
                        path = root / Path(req).parent / match.group(1)
                else:
                    path = root / req
                extra_part = f"[{','.join(sorted(extras))}]" if extras else ""
                rel_path = path.resolve().relative_to(root)
                self._requirement = f"{rel_path}{extra_part}"
        self._options = options
        self._from_file = from_file
        self._lineno = lineno

    @property
    def requirement(self) -> Union[Requirement, Path, str]:
        return self._requirement

    @property
    def from_file(self) -> str:
        return self._from_file

    @property
    def lineno(self) -> int:
        return self._lineno

    @property
    def options(self) -> Dict[str, Any]:
        return self._options

    def __repr__(self) -> str:
        base = f"{self.__class__.__name__}(requirement={self._requirement}, "
        if self._options:
            base += f"options={self._options!r}, "
        return f"{base.rstrip(', ')})"

    def __str__(self) -> str:
        result = []
        if self.options.get("is_constraint"):
            result.append("-c")
        if self.options.get("is_editable"):
            result.append("-e")
        result.append(str(self.requirement))
        for hash_value in self.options.get("hash", []):
            result.extend(("--hash", hash_value))
        return " ".join(result)


class _ParsedLine:
    def __init__(self, filename: str, lineno: int, args: str, opts: Namespace, constraint: bool) -> None:
        self.filename = filename
        self.lineno = lineno
        self.opts = opts
        self.constraint = constraint
        if args:
            self.is_requirement = True
            self.is_editable = False
            self.requirement = args
        elif opts.editables:
            self.is_requirement = True
            self.is_editable = True
            # We don't support multiple -e on one line
            self.requirement = opts.editables[0]
        else:
            self.is_requirement = False


class RequirementsFile:
    def __init__(self, path: Path, constraint: bool) -> None:
        self._path = path
        self._is_constraint: bool = constraint
        self._opt = Namespace()
        self._result: List[ParsedRequirement] = []
        self._loaded = False
        self._parser_private: Optional[ArgumentParser] = None

    def __str__(self) -> str:
        return f"{'-c' if self.is_constraint else '-r'} {self.path}"

    @property
    def path(self) -> Path:
        return self._path

    @property
    def is_constraint(self) -> bool:
        return self._is_constraint

    @property
    def options(self) -> Namespace:
        self._parse_requirements()
        return self._opt

    @property
    def requirements(self) -> List[ParsedRequirement]:
        self._parse_requirements()
        return self._result

    @property
    def _parser(self) -> ArgumentParser:
        if self._parser_private is None:
            self._parser_private = build_parser(False)
        return self._parser_private

    def _parse_requirements(self) -> None:
        if self._loaded:
            return
        self._result, found = [], set()
        for parsed_line in self._parse_and_recurse(str(self._path), self.is_constraint):
            parsed_req = self._handle_line(parsed_line)
            if parsed_req is not None:
                key = str(parsed_req)
                if key not in found:
                    found.add(key)
                    self._result.append(parsed_req)

        def key_func(line: ParsedRequirement) -> Tuple[int, Tuple[int, str, str]]:
            of_type = {Requirement: 0, Path: 1, str: 2}[type(line.requirement)]
            between = of_type, str(line.requirement).lower(), str(line.options)
            if "is_constraint" in line.options:
                return 2, between
            if "is_editable" in line.options:
                return 1, between
            return 0, between

        self._result.sort(key=key_func)
        self._loaded = True

    def _parse_and_recurse(self, filename: str, constraint: bool) -> Iterator[_ParsedLine]:
        for line in self._parse_file(filename, constraint):
            if not line.is_requirement and (line.opts.requirements or line.opts.constraints):
                if line.opts.requirements:  # parse a nested requirements file
                    nested_constraint, req_path = False, line.opts.requirements[0]
                else:
                    nested_constraint, req_path = True, line.opts.constraints[0]
                if _SCHEME_RE.search(filename):  # original file is over http
                    req_path = urllib.parse.urljoin(filename, req_path)  # do a url join so relative paths work
                elif not _SCHEME_RE.search(req_path):  # original file and nested file are paths
                    # do a join so relative paths work
                    req_path = os.path.join(os.path.dirname(filename), req_path)
                yield from self._parse_and_recurse(req_path, nested_constraint)
            else:
                yield line

    def _parse_file(self, url: str, constraint: bool) -> Iterator[_ParsedLine]:
        content = self._get_file_content(url)
        for line_number, line in self._pre_process(content):
            args_str, opts = self._parse_line(line)
            yield _ParsedLine(url, line_number, args_str, opts, constraint)

    def _get_file_content(self, url: str) -> str:
        """
        Gets the content of a file; it may be a filename, file: URL, or http: URL.  Returns (location, content).
        Content is unicode. Respects # -*- coding: declarations on the retrieved files.

        :param url:         File path or url.
        """
        scheme = get_url_scheme(url)
        if scheme in ["http", "https"]:
            with urlopen(url) as response:
                text = self._read_decode(response)
                return text
        elif scheme == "file":
            url = url_to_path(url)
        try:
            with open(url, "rb") as file_handler:
                text = self._read_decode(file_handler)
        except OSError as exc:
            raise ValueError(f"Could not open requirements file: {exc}")
        return text

    @staticmethod
    def _read_decode(file_handler: IO[bytes]) -> str:
        raw = file_handler.read()
        if not raw:
            return ""
        codec = chardet.detect(raw)["encoding"]
        text = raw.decode(codec)
        return text

    def _pre_process(self, content: str) -> ReqFileLines:
        """Split, filter, and join lines, and return a line iterator

        :param content: the content of the requirements file
        """
        lines_enum: ReqFileLines = enumerate(content.splitlines(), start=1)  # noqa
        lines_enum = self._join_lines(lines_enum)
        lines_enum = self._ignore_comments(lines_enum)
        lines_enum = self._expand_env_variables(lines_enum)
        return lines_enum

    def _parse_line(self, line: str) -> Tuple[str, Namespace]:
        args_str, options_str = self._break_args_options(line)
        args = shlex.split(options_str)
        opts = self._parser.parse_args(args)
        return args_str, opts

    def _handle_line(self, line: _ParsedLine) -> Optional[ParsedRequirement]:
        """
        Handle a single parsed requirements line; This can result in creating/yielding requirements or updating options.

        :param line: The parsed line to be processed.

        Returns a ParsedRequirement object if the line is a requirement line, otherwise returns None.

        For lines that contain requirements, the only options that have an effect are from SUPPORTED_OPTIONS_REQ, and
        they are scoped to the requirement. Other options from SUPPORTED_OPTIONS may be present, but are ignored.

        For lines that do not contain requirements, the only options that have an effect are from SUPPORTED_OPTIONS.
        Options from SUPPORTED_OPTIONS_REQ may be present, but are ignored. These lines may contain multiple options
        (although our docs imply only one is supported), and all our parsed and affect the finder.
        """
        if line.is_requirement:
            parsed_req = self._handle_requirement_line(line)
            return parsed_req
        else:
            self._handle_option_line(line.opts, line.filename)
            return None

    @staticmethod
    def _handle_requirement_line(line: _ParsedLine) -> ParsedRequirement:
        # For editable requirements, we don't support per-requirement options, so just return the parsed requirement.
        # get the options that apply to requirements
        req_options = {}
        if line.is_editable:
            req_options["is_editable"] = line.is_editable
        if line.constraint:
            req_options["is_constraint"] = line.constraint
        hash_values = getattr(line.opts, "hash", [])
        if hash_values:
            req_options["hash"] = hash_values
        return ParsedRequirement(line.requirement, req_options, line.filename, line.lineno)

    def _handle_option_line(self, opts: Namespace, filename: str) -> None:  # noqa: C901
        # percolate options upward
        if opts.require_hashes:
            self._opt.require_hashes = True
        if opts.features_enabled:
            if not hasattr(self._opt, "features_enabled"):
                self._opt.features_enabled = []
            for feature in opts.features_enabled:
                if feature not in self._opt.features_enabled:
                    self._opt.features_enabled.append(feature)
            self._opt.features_enabled.sort()
        if opts.index_url:
            if not hasattr(self._opt, "index_url"):
                self._opt.index_url = []
            self._opt.index_url = [opts.index_url]
        if opts.no_index is True:
            self._opt.index_url = []
        if opts.extra_index_url:
            if not hasattr(self._opt, "index_url"):
                self._opt.index_url = []
            for url in opts.extra_index_url:
                if url not in self._opt.index_url:
                    self._opt.index_url.extend(opts.extra_index_url)
        if opts.find_links:
            # FIXME: it would be nice to keep track of the source of the find_links: support a find-links local path
            # relative to a requirements file.
            if not hasattr(self._opt, "index_url"):  # pragma: no branch
                self._opt.find_links = []
            value = opts.find_links[0]
            req_dir = os.path.dirname(os.path.abspath(filename))
            relative_to_reqs_file = os.path.join(req_dir, value)
            if os.path.exists(relative_to_reqs_file):
                value = relative_to_reqs_file  # pragma: no cover
            if value not in self._opt.find_links:  # pragma: no branch
                self._opt.find_links.append(value)
        if opts.pre:
            self._opt.pre = True
        if opts.prefer_binary:
            self._opt.prefer_binary = True
        for host in opts.trusted_host or []:
            if not hasattr(self._opt, "trusted_hosts"):
                self._opt.trusted_hosts = []
            if host not in self._opt.trusted_hosts:
                self._opt.trusted_hosts.append(host)

    @staticmethod
    def _break_args_options(line: str) -> Tuple[str, str]:
        """
        Break up the line into an args and options string.  We only want to shlex (and then optparse) the options, not
        the args. args can contain markers which are corrupted by shlex.
        """
        tokens = line.split(" ")
        args = []
        options = tokens[:]
        for token in tokens:
            if token.startswith("-") or token.startswith("--"):
                break
            else:
                args.append(token)
                options.pop(0)
        return " ".join(args), " ".join(options)

    @staticmethod
    def _join_lines(lines_enum: ReqFileLines) -> ReqFileLines:
        """
        Joins a line ending in '\' with the previous line (except when following comments). The joined line takes on the
        index of the first line.
        """
        primary_line_number = None
        new_line: List[str] = []
        for line_number, line in lines_enum:
            if not line.endswith("\\") or _COMMENT_RE.match(line):
                if _COMMENT_RE.match(line):
                    line = f" {line}"  # this ensures comments are always matched later
                if new_line:
                    new_line.append(line)
                    assert primary_line_number is not None
                    yield primary_line_number, "".join(new_line)
                    new_line = []
                else:
                    yield line_number, line
            else:
                if not new_line:  # pragma: no branch
                    primary_line_number = line_number
                new_line.append(line.strip("\\"))
        # last line contains \
        if new_line:
            assert primary_line_number is not None
            yield primary_line_number, "".join(new_line)

    @staticmethod
    def _ignore_comments(lines_enum: ReqFileLines) -> ReqFileLines:
        """Strips comments and filter empty lines."""
        for line_number, line in lines_enum:
            line = _COMMENT_RE.sub("", line)
            line = line.strip()
            if line:
                yield line_number, line

    @staticmethod
    def _expand_env_variables(lines_enum: ReqFileLines) -> ReqFileLines:
        """Replace all environment variables that can be retrieved via `os.getenv`.

        The only allowed format for environment variables defined in the requirement file is `${MY_VARIABLE_1}` to
        ensure two things:

        1. Strings that contain a `$` aren't accidentally (partially) expanded.
        2. Ensure consistency across platforms for requirement files.

        These points are the result of a discussion on the `github pull request #3514
        <https://github.com/pypa/pip/pull/3514>`_. Valid characters in variable names follow the `POSIX standard
        <http://pubs.opengroup.org/onlinepubs/9699919799/>`_ and are limited to uppercase letter, digits and the `_`.
        """
        for line_number, line in lines_enum:
            for env_var, var_name in _ENV_VAR_RE.findall(line):
                value = os.getenv(var_name)
                if not value:
                    continue
                line = line.replace(env_var, value)
            yield line_number, line


__all__ = (
    "RequirementsFile",
    "ReqFileLines",
    "ParsedRequirement",
)
