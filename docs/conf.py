from __future__ import annotations

import re
import sys
from datetime import date, datetime
from importlib.machinery import SourceFileLoader
from pathlib import Path
from subprocess import check_output
from typing import Any

from docutils.nodes import Element, reference
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.domains.python import PythonDomain
from sphinx.environment import BuildEnvironment
from sphinx.ext.autodoc import Options
from sphinx.ext.extlinks import ExternalLinksChecker

from tox import __version__

company, name = "tox-dev", "tox"
release, version = __version__, ".".join(__version__.split(".")[:2])
copyright = f"2010-{date.today().year}, {company}"
master_doc, source_suffix = "index", ".rst"

html_theme = "furo"
html_title, html_last_updated_fmt = "tox", datetime.now().isoformat()
pygments_style, pygments_dark_style = "sphinx", "monokai"
html_static_path, html_css_files = ["_static"], ["custom.css"]
html_logo, html_favicon = "_static/img/tox.svg", "_static/img/toxfavi.ico"

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

exclude_patterns = ["_build", "changelog/*", "_draft.rst"]
autoclass_content, autodoc_member_order, autodoc_typehints = "class", "bysource", "none"
autodoc_default_options = {
    "member-order": "bysource",
    "undoc-members": True,
    "show-inheritance": True,
}
autosectionlabel_prefix_document = True

extlinks = {
    "issue": ("https://github.com/tox-dev/tox/issues/%s", "#"),
    "pull": ("https://github.com/tox-dev/tox/pull/%s", "PR #"),
    "discussion": ("https://github.com/tox-dev/tox/discussions/%s", "#"),
    "user": ("https://github.com/%s", "@"),
    "gh_repo": ("https://github.com/%s", ""),
    "gh": ("https://github.com/%s", ""),
    "pypi": ("https://pypi.org/project/%s", ""),
}
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "packaging": ("https://packaging.pypa.io/en/latest", None),
}
nitpicky = True
nitpick_ignore = []
linkcheck_workers = 10
linkcheck_ignore = [re.escape(r"https://github.com/tox-dev/tox/issues/new?title=Trouble+with+development+environment")]
extlinks_detect_hardcoded_links = True


def process_signature(
    app: Sphinx,  # noqa: U100
    objtype: str,
    name: str,  # noqa: U100
    obj: Any,  # noqa: U100
    options: Options,
    args: str,  # noqa: U100
    retann: str | None,  # noqa: U100
) -> None | tuple[None, None]:
    # skip-member is not checked for class level docs, so disable via signature processing
    return (None, None) if objtype == "class" and "__init__" in options.get("exclude-members", set()) else None


def setup(app: Sphinx) -> None:
    here = Path(__file__).parent
    # 1. run towncrier
    root, exe = here.parent, Path(sys.executable)
    towncrier = exe.with_name(f"towncrier{exe.suffix}")
    new = check_output([str(towncrier), "--draft", "--version", "NEXT"], cwd=root, universal_newlines=True)
    (root / "docs" / "_draft.rst").write_text("" if "No significant changes" in new else new)

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
                "tox.config.of_type.T": "typing.TypeVar",  # used by Sphinx bases
                "tox.config.loader.api.T": "typing.TypeVar",  # used by Sphinx bases
                "tox.config.loader.convert.T": "typing.TypeVar",  # used by Sphinx bases
                "tox.tox_env.installer.T": "typing.TypeVar",  # used by Sphinx bases
                "concurrent.futures._base.Future": "concurrent.futures.Future",
            }
            if target in mapping:
                target = node["reftarget"] = mapping[target]
                # node.children[0].children[0] = Text(target, target)
            return super().resolve_xref(env, fromdocname, builder, type, target, node, contnode)

    app.connect("autodoc-process-signature", process_signature, priority=400)
    app.add_domain(PatchedPythonDomain, override=True)
    tox_cfg = SourceFileLoader("tox_conf", str(here / "tox_conf.py")).load_module().ToxConfig
    app.add_directive(tox_cfg.name, tox_cfg)

    def check_uri(self, refnode: reference) -> None:
        if refnode.document.attributes["source"].endswith("index.rst"):
            return  # do not use for the index file
        return prev_check(self, refnode)

    prev_check, ExternalLinksChecker.check_uri = ExternalLinksChecker.check_uri, check_uri
