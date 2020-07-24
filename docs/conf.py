import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

import sphinx_rtd_theme

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
]

templates_path = []
unused_docs = []
source_suffix = ".rst"
exclude_patterns = ["_build", "changelog/*", "_draft.rst"]

master_doc = "index"
pygments_style = "default"
always_document_param_types = True
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
autoclass_content = "both"  # Include __init__ in class documentation
autodoc_member_order = "bysource"
autosectionlabel_prefix_document = True

extlinks = {
    "issue": ("https://github.com/tox-dev/tox/issues/%s", "#"),
    "pull": ("https://github.com/tox-dev/tox/pull/%s", "PR #"),
    "user": ("https://github.com/%s", "@"),
    "pypi": ("https://pypi.org/project/%s", ""),
}


def generate_draft_news():
    root = Path(__file__).parents[1]
    exe = Path(sys.executable)
    towncrier = exe.with_name(f"towncrier{exe.suffix}")
    new = subprocess.check_output([str(towncrier), "--draft", "--version", "NEXT"], cwd=root, universal_newlines=True)
    (root / "docs" / "_draft.rst").write_text("" if "No significant changes" in new else new)


generate_draft_news()


def setup(app):
    app.add_css_file("custom.css")
