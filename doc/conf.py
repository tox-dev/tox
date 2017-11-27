import os
import sys
from datetime import date

from pkg_resources import get_distribution

sys.path.insert(0, os.path.dirname(__file__))
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
html_theme = 'alabaster'
html_logo = 'img/tox.png'
html_favicon = 'img/toxfavi.ico'
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
