import os
import re
import subprocess
from datetime import date
from pathlib import Path

from pkg_resources import get_distribution

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
]
ROOT_SRC_TREE_DIR = Path(__file__).parents[1]


def generate_draft_news():
    home = "https://github.com"
    issue = "{}/issue".format(home)
    fragments_path = ROOT_SRC_TREE_DIR / "changelog"
    for pattern, replacement in (
        (r"[^`]@([^,\s]+)", r"`@\1 <{}/\1>`_".format(home)),
        (r"[^`]#([\d]+)", r"`#pr\1 <{}/\1>`_".format(issue)),
    ):
        for path in fragments_path.glob("*.rst"):
            path.write_text(re.sub(pattern, replacement, path.read_text()))
    changelog = subprocess.check_output(
        ["towncrier", "--draft", "--version", "DRAFT"], cwd=str(ROOT_SRC_TREE_DIR)
    ).decode("utf-8")
    if "No significant changes" in changelog:
        content = ""
    else:
        note = "Changes in master, but not released yet are under the draft section.\n\n"
        content = "{}\n\n{}".format(note, changelog)
    (ROOT_SRC_TREE_DIR / "_draft.rst").write_text(content)


generate_draft_news()

project = u"tox"
_full_version = get_distribution(project).version
release = _full_version.split("+", 1)[0]
version = ".".join(release.split(".")[:2])

author = "holger krekel and others"
year = date.today().year
copyright = u"2010-{}, {}".format(year, author)

master_doc = "index"
source_suffix = ".rst"

exclude_patterns = ["_build"]

templates_path = ["_templates"]
pygments_style = "sphinx"

html_theme = "alabaster"
html_theme_options = {
    "logo": "img/tox.png",
    "github_user": "tox-dev",
    "github_repo": "tox",
    "description": "standardise testing in Python",
    "github_banner": "true",
    "travis_button": "true",
    "badge_branch": "master",
    "fixed_sidebar": "false",
}
html_sidebars = {
    "**": ["about.html", "localtoc.html", "relations.html", "searchbox.html", "donate.html"]
}
html_show_sourcelink = False
html_static_path = ["_static"]
htmlhelp_basename = "{}doc".format(project)
latex_documents = [("index", "tox.tex", u"{} Documentation".format(project), author, "manual")]
man_pages = [("index", project, u"{} Documentation".format(project), [author], 1)]
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

intersphinx_mapping = {"https://docs.python.org/": None}


def setup(app):
    # from sphinx.ext.autodoc import cut_lines
    # app.connect('autodoc-process-docstring', cut_lines(4, what=['module']))
    app.add_object_type(
        "confval",
        "confval",
        objname="configuration value",
        indextemplate="pair: %s; configuration value",
    )


tls_cacerts = os.getenv("SSL_CERT_FILE")  # we don't care here about the validity of certificates
linkcheck_timeout = 30
linkcheck_ignore = [r"http://holgerkrekel.net"]

extlinks = {
    "issue": ("https://github.com/tox-dev/tox/issues/%s", "#"),
    "pull": ("https://github.com/tox-dev/tox/pull/%s", "p"),
    "user": ("https://github.com/%s", "@"),
}
