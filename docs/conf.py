from __future__ import annotations

import os
import re
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

from truststore import inject_into_ssl

from tox import __version__

if TYPE_CHECKING:
    from docutils.nodes import Element
    from sphinx.addnodes import pending_xref
    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.ext.autodoc import Options

company, name = "tox-dev", "tox"
project = name
release, version = __version__, ".".join(__version__.split(".")[:2])
copyright = f"{company}"  # ruff:ignore[builtin-variable-shadowing]
html_theme = "furo"
html_theme_options = {
    "sidebar_hide_name": True,
}
html_title, html_last_updated_fmt = "tox", "%Y-%m-%dT%H:%M:%S"
html_show_sourcelink = False
pygments_style, pygments_dark_style = "sphinx", "monokai"
html_static_path, html_css_files = ["_static"], ["custom.css"]
html_js_files = ["mermaid-reset.js"]
html_logo, html_favicon = "_static/img/tox.svg", "_static/img/toxfavi.ico"

extensions = [
    "sphinx_llm.txt",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx_argparse_cli",
    "sphinx_autodoc_typehints",
    "sphinx_inline_tabs",
    "sphinx_copybutton",
    "sphinx_issues",  # :user: and similar roles
    "sphinxcontrib.mermaid",
    "sphinxcontrib.towncrier.ext",
    "sphinx_reredirects",
]
mermaid_output_format = "raw"
mermaid_d3_zoom = True
mermaid_height = "auto"

exclude_patterns = ["_build", "changelog/*"]
autodoc_member_order, autodoc_typehints = "bysource", "none"
autodoc_default_options = {
    "undoc-members": True,
    "show-inheritance": True,
}
autosectionlabel_prefix_document = True
autosectionlabel_maxdepth = 2

extlinks = {
    "discussion": ("https://github.com/tox-dev/tox/discussions/%s", "#%s"),
    "gh_repo": ("https://github.com/%s", "%s"),
    "gh": ("https://github.com/%s", "%s"),
}
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "packaging": ("https://packaging.pypa.io/en/latest", None),
}
nitpicky = True
# a private stdlib class we cannot document, the stdlib itself has no public name for it
nitpick_ignore = [("py:class", "argparse._ArgumentGroup")]
linkcheck_workers = 10
linkcheck_exclude_documents = [r"^index$"]
linkcheck_ignore = [
    re.escape(i)
    for i in (
        r"https://github.com/tox-dev/tox/issues/new?title=Trouble+with+development+environment",
        r"https://porkbun.com/",  # has captcha on it that makes it return with 405
        r"https://opensource.org/license/mit",
    )
]
linkcheck_allowed_redirects = {r"https://github.com/tox-dev/tox/issues/\d+": r"https://github.com/tox-dev/tox/pull/\d+"}
extlinks_detect_hardcoded_links = True

issues_github_path = f"{company}/{name}"  # `sphinx-issues` ext

# Man page configuration
man_pages = [("man/tox.1", "tox", "virtualenv-based automation of test activities", [], 1)]
man_show_urls = True

redirects = {
    "config": "reference/config.html",
    "cli_interface": "reference/cli.html",
    "user_guide": "explanation.html",
    "installation": "how-to/install.html",
    "howto": "how-to/usage.html",
    "getting_started": "tutorial/getting-started.html",
    "plugins": "plugin/index.html",
    "plugins_api": "plugin/api.html",
    "plugins/index": "plugin/index.html",
    "plugins/api": "plugin/api.html",
    "plugins/getting_started": "plugin/getting_started.html",
    "plugins/howto": "plugin/howto.html",
    "upgrading": "index.html",
    "faq": "index.html",
    "example/general": "index.html",
    "example/basic": "index.html",
    "example/devenv": "index.html",
    "example/documentation": "index.html",
    "example/jenkins": "index.html",
    "example/nose": "index.html",
    "example/package": "index.html",
    "example/platform": "index.html",
    "example/pytest": "index.html",
    "example/result": "index.html",
    "example/unittest": "index.html",
}

towncrier_draft_autoversion_mode = "draft"
towncrier_draft_include_empty = True
towncrier_draft_working_directory = Path(__file__).parent.parent


def setup(app: Sphinx) -> None:
    app.connect("autodoc-process-signature", process_signature, priority=400)
    # Rewrite aliases before intersphinx tries to resolve them.
    app.connect("missing-reference", rewrite_missing_reference, priority=400)
    tox_conf_loader = SourceFileLoader("tox_conf", str(Path(__file__).parent / "tox_conf.py"))
    tox_conf = ModuleType(tox_conf_loader.name)
    tox_conf_loader.exec_module(tox_conf)
    tox_cfg = tox_conf.ToxConfig
    app.add_directive(tox_cfg.name, tox_cfg)

    inject_into_ssl()


def process_signature(  # ruff:ignore[too-many-arguments]
    app: Sphinx,  # ruff:ignore[unused-function-argument]
    objtype: str,
    name: str,  # ruff:ignore[unused-function-argument]
    obj: Any,  # ruff:ignore[unused-function-argument]
    options: Options,
    args: str | None,  # ruff:ignore[unused-function-argument]
    retann: str | None,  # ruff:ignore[unused-function-argument]
) -> tuple[None, None] | None:
    # skip-member is not checked for class level docs, so disable via signature processing
    if objtype == "class" and (exclude := options.get("exclude-members")) and "__init__" in exclude:
        return None, None
    return None


def rewrite_missing_reference(_app: Sphinx, _env: BuildEnvironment, node: pending_xref, _contnode: Element) -> None:
    mapping = {
        "tox.config.of_type.T": "typing.TypeVar",
        "tox.config.loader.api.T": "typing.TypeVar",
        "tox.config.loader.convert.T": "typing.TypeVar",
        "tox.tox_env.installer.EnvT_co": "typing.TypeVar",
        "tox.tox_env.installer.ArgsT": "typing.TypeVar",
        "pathlib._local.Path": "pathlib.Path",
        "argparse._ActionsContainer.add_argument_group": "argparse.ArgumentParser.add_argument_group",
        "argparse._ActionsContainer.add_argument": "argparse.ArgumentParser.add_argument",
    }
    if target := mapping.get(node["reftarget"]):
        node["reftarget"] = target


markdown_http_base = os.environ.get("READTHEDOCS_CANONICAL_URL", "")
