import sys
from datetime import date, datetime
from pathlib import Path
from subprocess import check_output
from typing import Any, Optional, Tuple, Union

import sphinx_rtd_theme
from docutils.nodes import Element
from sphinx.addnodes import pending_xref
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.environment import BuildEnvironment
from sphinx.ext.autodoc import Options

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
    app: Sphinx, objtype: str, name: str, obj: Any, options: Options, args: str, retann: Optional[str]  # noqa: U100
) -> Union[None, Tuple[None, None]]:
    # skip-member is not checked for class level docs, so disable via signature processing
    return (None, None) if objtype == "class" and "__init__" in options.get("exclude-members", set()) else None


def setup(app: Sphinx) -> None:
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
            }
            if target in mapping:
                node["reftarget"] = mapping[target]
            return super().resolve_xref(env, fromdocname, builder, type, target, node, contnode)

    app.connect("autodoc-skip-member", skip_member)
    app.connect("autodoc-process-signature", process_signature, priority=400)
    app.add_domain(PatchedPythonDomain, override=True)
    app.add_css_file("custom.css")
