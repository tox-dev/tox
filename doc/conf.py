import os
import subprocess
import sys
from datetime import date

from pkg_resources import get_distribution

here = os.path.dirname(__file__)
sys.path.insert(0, here)
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.extlinks',
              'sphinx.ext.intersphinx',
              'sphinx.ext.viewcode']

project = u'tox'
_full_version = get_distribution(project).version
release = _full_version.split('+', 1)[0]
version = '.'.join(release.split('.')[:2])

author = 'holger krekel and others'
year = date.today().year
copyright = u'2010-{}, {}'.format(year, author)

master_doc = 'index'
source_suffix = '.rst'

exclude_patterns = ['_build']

templates_path = ['_templates']
pygments_style = 'sphinx'
html_theme = 'sphinxdoc'
html_static_path = ['_static']
html_show_sourcelink = False
htmlhelp_basename = '{}doc'.format(project)
latex_documents = [('index', 'tox.tex', u'{} Documentation'.format(project),
                    author, 'manual')]
man_pages = [('index', project, u'{} Documentation'.format(project),
              [author], 1)]
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

intersphinx_mapping = {'https://docs.python.org/': None}


def setup(app):
    # from sphinx.ext.autodoc import cut_lines
    # app.connect('autodoc-process-docstring', cut_lines(4, what=['module']))
    app.add_description_unit('confval', 'confval',
                             objname='configuration value',
                             indextemplate='pair: %s; configuration value')


tls_cacerts = os.getenv('SSL_CERT_FILE')  # we don't care here about the validity of certificates
linkcheck_timeout = 30
linkcheck_ignore = [r'http://holgerkrekel.net']

extlinks = {'issue': ('https://github.com/tox-dev/tox/issues/%s', '#'),
            'pull': ('https://github.com/tox-dev/tox/pull/%s', 'p'),
            'user': ('https://github.com/%s', '@')}


def generate_newsfragments():
    """
    generate and include into the changelog news fragments so they are also subject to the CI,
    whenever a new release is done there should be no news fragment and as such this will have
    no effect
    """
    current_path = os.getcwd()
    project_root = os.path.join(here, os.path.pardir)
    try:
        os.chdir(project_root)
        with open('.tox/docs/fragments.rst', 'w') as f:
            cmd = ['towncrier', '--draft', '--dir', project_root]
            out = subprocess.check_output(cmd).decode('utf-8').strip()
            f.write(out)
    finally:
        os.chdir(current_path)


generate_newsfragments()
