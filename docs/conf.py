from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from subprocess import check_output
from typing import Any, cast

import sphinx_rtd_theme
from docutils.nodes import Element, Node, Text, container, fully_normalize_name, literal, paragraph, reference, strong
from docutils.parsers.rst.directives import flag, unchanged, unchanged_required
from docutils.parsers.rst.states import RSTState, RSTStateMachine
from docutils.statemachine import StringList, string2lines
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.domains.std import StandardDomain
from sphinx.environment import BuildEnvironment
from sphinx.ext.autodoc import Options
from sphinx.locale import __
from sphinx.util.docutils import SphinxDirective
from sphinx.util.logging import getLogger

from tox.version import __version__

company = "tox-dev"
name = "tox"
version = ".".join(__version__.split(".")[:2])
release = __version__
copyright = f"2010-{date.today().year}, {company}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx_argparse_cli",
    "sphinx_autodoc_typehints",
    "sphinx_inline_tabs",
    "sphinx_copybutton",
]

templates_path = []
unused_docs = []
source_suffix = ".rst"
exclude_patterns = ["_build", "changelog/*", "_draft.rst"]

master_doc = "index"
pygments_style = "default"

project = name
today_fmt = "%B %d, %Y"

html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
html_theme_options = {
    "canonical_url": "https://tox.readthedocs.io/en/latest/",
    "logo_only": False,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "collapse_navigation": False,
    "sticky_navigation": True,
    "navigation_depth": 6,
    "includehidden": True,
}
html_static_path = ["_static"]
html_last_updated_fmt = datetime.now().isoformat()
html_logo = "_static/img/tox.svg"
html_favicon = "_static/img/toxfavi.ico"
htmlhelp_basename = "Pastedoc"

autoclass_content = "class"
autodoc_member_order = "bysource"
autodoc_default_options = {
    "member-order": "bysource",
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_typehints = "none"
always_document_param_types = False
typehints_fully_qualified = True
autosectionlabel_prefix_document = True

extlinks = {
    "issue": ("https://github.com/tox-dev/tox/issues/%s", "#"),
    "pull": ("https://github.com/tox-dev/tox/pull/%s", "PR #"),
    "user": ("https://github.com/%s", "@"),
    "pypi": ("https://pypi.org/project/%s", ""),
}
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "packaging": ("https://packaging.pypa.io/en/latest", None),
}
nitpicky = True
nitpick_ignore = []


def skip_member(app: Sphinx, what: str, name: str, obj: Any, would_skip: bool, options: Options) -> bool:  # noqa: U100
    return name in options.get("exclude-members", set()) or would_skip


def process_signature(
    app: Sphinx, objtype: str, name: str, obj: Any, options: Options, args: str, retann: str | None  # noqa: U100
) -> None | tuple[None, None]:
    # skip-member is not checked for class level docs, so disable via signature processing
    return (None, None) if objtype == "class" and "__init__" in options.get("exclude-members", set()) else None


def setup(app: Sphinx) -> None:
    logger = getLogger(__name__)

    root = Path(__file__).parents[1]
    exe = Path(sys.executable)
    towncrier = exe.with_name(f"towncrier{exe.suffix}")
    new = check_output([str(towncrier), "--draft", "--version", "NEXT"], cwd=root, universal_newlines=True)
    (root / "docs" / "_draft.rst").write_text("" if "No significant changes" in new else new)

    from sphinx.domains.python import PythonDomain

    class PatchedPythonDomain(PythonDomain):
        def resolve_xref(
            self,
            env: BuildEnvironment,
            fromdocname: str,
            builder: Builder,
            type: str,
            target: str,
            node: pending_xref,
            contnode: Element,
        ) -> Element:
            # fixup some wrongly resolved mappings
            mapping = {
                "_io.TextIOWrapper": "io.TextIOWrapper",
                "Future": "concurrent.futures.Future",
                "_F": "typing.TypeVar",
                "V": "typing.TypeVar",
                "T": "typing.TypeVar",
                "tox.config.of_type.T": "typing.TypeVar",
                "tox.config.loader.api.T": "typing.TypeVar",
                "tox.config.loader.convert.T": "typing.TypeVar",
                "tox.tox_env.installer.T": "typing.TypeVar",
            }
            if target in mapping:
                node["reftarget"] = mapping[target]

            return super().resolve_xref(env, fromdocname, builder, type, target, node, contnode)

    app.connect("autodoc-skip-member", skip_member)
    app.connect("autodoc-process-signature", process_signature, priority=400)
    app.add_domain(PatchedPythonDomain, override=True)
    app.add_css_file("custom.css")

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
                name, arguments, options, content, lineno, content_offset, block_text, state, state_machine
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
                logger.warning(
                    __("duplicate label %s, other instance in %s"),
                    of_name,
                    self.env.doc2path(self._std_domain.labels[of_name][0]),
                    location=node,
                    type="sphinx-argparse-cli",
                    subtype=self.env.docname,
                )
            self._std_domain.anonlabels[of_name] = doc_name, ref_name
            self._std_domain.labels[of_name] = doc_name, ref_name, ref_title

    app.add_directive(ToxConfig.name, ToxConfig)
