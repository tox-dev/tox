from __future__ import annotations

from typing import cast

from docutils.nodes import Element, Node, Text, container, fully_normalize_name, literal, paragraph, reference, strong
from docutils.parsers.rst.directives import flag, unchanged, unchanged_required
from docutils.parsers.rst.states import RSTState, RSTStateMachine
from docutils.statemachine import StringList, string2lines
from sphinx.domains.std import StandardDomain
from sphinx.locale import __
from sphinx.util.docutils import SphinxDirective
from sphinx.util.logging import getLogger

LOGGER = getLogger(__name__)


class ToxConfig(SphinxDirective):
    name = "conf"
    has_content = True
    option_spec = {
        "keys": unchanged_required,
        "version_added": unchanged,
        "version_changed": unchanged,
        "default": unchanged,
        "constant": flag,
        "ref_suffix": unchanged,
    }

    def __init__(
        self,
        name: str,
        arguments: list[str],
        options: dict[str, str],
        content: StringList,
        lineno: int,
        content_offset: int,
        block_text: str,
        state: RSTState,
        state_machine: RSTStateMachine,
    ):
        super().__init__(
            name,
            arguments,
            options,
            content,
            lineno,
            content_offset,
            block_text,
            state,
            state_machine,
        )
        self._std_domain: StandardDomain = cast(StandardDomain, self.env.get_domain("std"))

    def run(self) -> list[Node]:
        self.env.note_reread()  # this document needs to be always updated

        line = paragraph()
        line += Text("■" if "constant" in self.options else "⚙️")
        for key in (i.strip() for i in self.options["keys"].split(",")):
            line += Text(" ")
            self._mk_key(line, key)
        if "default" in self.options:
            default = self.options["default"]
            line += Text(" with default value of ")
            line += literal(default, default)
        if "version_added" in self.options:
            line += Text(" 📢 added in ")
            ver = self.options["version_added"]
            line += literal(ver, ver)

        p = container("")
        self.state.nested_parse(StringList(string2lines("\n".join(f"    {i}" for i in self.content))), 0, p)
        line += p

        return [line]

    def _mk_key(self, line: paragraph, key: str) -> None:
        ref_id = key if "ref_suffix" not in self.options else f"{key}-{self.options['ref_suffix']}"
        ref = reference("", refid=ref_id, reftitle=key)
        line.attributes["ids"].append(ref_id)
        st = strong()
        st += literal(text=key)
        ref += st
        self._register_ref(ref_id, ref_id, ref)
        line += ref

    def _register_ref(self, ref_name: str, ref_title: str, node: Element) -> None:
        of_name, doc_name = fully_normalize_name(ref_name), self.env.docname
        if of_name in self._std_domain.labels:
            LOGGER.warning(
                __("duplicate label %s, other instance in %s"),
                of_name,
                self.env.doc2path(self._std_domain.labels[of_name][0]),
                location=node,
                type="sphinx-argparse-cli",
                subtype=self.env.docname,
            )
        self._std_domain.anonlabels[of_name] = doc_name, ref_name
        self._std_domain.labels[of_name] = doc_name, ref_name, ref_title
