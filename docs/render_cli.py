import os
import re
from argparse import SUPPRESS, ArgumentParser, HelpFormatter
from collections import defaultdict, namedtuple
from typing import Dict, Iterator, List, Optional, Tuple

from docutils.nodes import (
    Body,
    Node,
    Text,
    bullet_list,
    list_item,
    literal,
    literal_block,
    paragraph,
    reference,
    section,
    title,
)
from docutils.parsers.rst.directives import unchanged_required
from docutils.parsers.rst.states import NestedStateMachine
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective

TextAsDefault = namedtuple("TextAsDefault", ["text"])


def make_id(key: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"\W", "-", key)).rstrip("-").lower()


class CliApi(SphinxDirective):
    name = "cli_api"
    has_content = False
    option_spec = dict(module=unchanged_required, func=unchanged_required)

    def __init__(
        self,
        name: str,
        arguments: List[str],
        options: Dict[str, str],
        content: StringList,
        lineno: int,
        content_offset: int,
        block_text: str,
        state: Body,
        state_machine: NestedStateMachine,
    ):
        super().__init__(name, arguments, options, content, lineno, content_offset, block_text, state, state_machine)
        self._parser: Optional[ArgumentParser] = None

    @property
    def parser(self) -> ArgumentParser:
        if self._parser is None:
            module_name, attr_name = self.options["module"], self.options["func"]
            parser_creator = getattr(__import__(module_name, fromlist=[attr_name]), attr_name)
            self._parser = parser_creator()
        return self._parser

    def load_sub_parsers(self) -> Iterator[Tuple[List[str], str, ArgumentParser]]:
        top_sub_parser = self.parser._subparsers  # noqa
        if not top_sub_parser:
            return
        parser_to_args: Dict[int, List[str]] = defaultdict(list)
        str_to_parser: Dict[str, ArgumentParser] = {}
        sub_parser = top_sub_parser._group_actions[0]  # noqa
        for key, parser in sub_parser._name_parser_map.items():  # noqa
            parser_to_args[id(parser)].append(key)
            str_to_parser[key] = parser
        for choice in sub_parser._choices_actions:  # noqa
            parser = str_to_parser[choice.dest]
            aliases = parser_to_args[id(parser)]
            aliases.remove(choice.dest)
            yield aliases, choice.help, parser

    def run(self) -> List[Node]:
        # construct headers
        title_text = f"{self.parser.prog} - CLI interface"
        home_section = section("", title("", Text(title_text)), ids=[make_id(title_text)], names=[title_text])
        if self.parser.description:
            desc_paragraph = paragraph("", Text(self.parser.description))
            home_section += desc_paragraph
        # construct groups excluding sub-parsers
        home_section += self._mk_usage(self.parser)
        for group in self.parser._action_groups:  # noqa
            if not group._group_actions or group is self.parser._subparsers:  # noqa
                continue
            home_section += self._mk_option_group(group, prefix="")
        # construct sub-parser
        if self.parser._subparsers:  # noqa
            for aliases, help_msg, parser in self.load_sub_parsers():
                home_section += self._mk_sub_command(aliases, help_msg, parser)
        return [home_section]

    def _mk_option_group(self, group, prefix):
        title_text = f"{prefix}{' ' if prefix else ''}{group.title}"
        ref_id = make_id(title_text)
        # the text sadly needs to be prefixed, because otherwise the autosectionlabel will conflict
        header = title("", Text(title_text))
        group_section = section("", header, ids=[ref_id], names=[ref_id])
        if group.description:
            group_section += paragraph("", Text(group.description))
        opt_group = bullet_list()
        for action in group._group_actions:  # noqa
            point = self._mk_option_line(action, prefix)
            opt_group += point
        group_section += opt_group
        return group_section

    def _mk_option_line(self, action, prefix):  # noqa
        line = paragraph()
        if action.option_strings:
            first = True
            for opt in action.option_strings:
                if first:
                    first = False
                else:
                    line += Text(", ")
                ref_id = make_id(f"{prefix}-{opt}")
                ref = reference("", refid=ref_id)
                line.attributes["ids"].append(ref_id)
                ref += literal(text=opt)
                line += ref
        else:
            ref_id = make_id(f"{prefix}-{action.metavar}")
            ref = reference("", refid=ref_id)
            line.attributes["ids"].append(ref_id)
            ref += literal(text=action.metavar)
            line += ref
        point = list_item("", line, ids=[])
        if action.help:
            line += Text(" - ")
            line += Text(action.help)
        if action.default != SUPPRESS:
            line += Text(" (default: ")
            line += literal(text=str(action.default).replace(os.getcwd(), "{cwd}"))
            line += Text(")")
        return point

    def _mk_sub_command(self, aliases, help_msg, parser):
        title_text = f"{parser.prog} ({', '.join(aliases)})"
        group_section = section("", title("", Text(title_text)), ids=[make_id(title_text)], names=[title_text])
        if help_msg:
            desc_paragraph = paragraph("", Text(help_msg))
            group_section += desc_paragraph
        group_section += self._mk_usage(parser)
        for group in parser._action_groups:  # noqa
            if not group._group_actions:  # noqa
                continue
            group_section += self._mk_option_group(group, prefix=parser.prog)
        return group_section

    def _mk_usage(self, parser):
        parser.formatter_class = lambda prog: HelpFormatter(prog, width=100)
        texts = parser.format_usage()[len("usage: ") :].splitlines()
        texts = [line if at == 0 else f"{' ' * (len(parser.prog) + 1)}{line.lstrip()}" for at, line in enumerate(texts)]
        return literal_block("", Text("\n".join(texts)))


__all__ = ("CliApi",)
