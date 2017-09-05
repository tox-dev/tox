import os
import sys

from pkg_resources import get_distribution

_full_version = get_distribution('tox').version
release = _full_version.split('+', 1)[0]
version = '.'.join(release.split('.')[:2])

sys.path.insert(0, os.path.dirname(__file__))
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.extlinks',
              'sphinx.ext.intersphinx',
              'sphinx.ext.viewcode']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'tox'
copyright = u'2015, holger krekel and others'
exclude_patterns = ['_build']
pygments_style = 'sphinx'
html_theme = 'sphinxdoc'
html_static_path = ['_static']
html_show_sourcelink = False
htmlhelp_basename = 'toxdoc'
latex_documents = [
    ('index', 'tox.tex', u'tox Documentation',
     u'holger krekel', 'manual'),
]
man_pages = [
    ('index', 'tox', u'tox Documentation',
     [u'holger krekel'], 1)
]
epub_title = u'tox'
epub_author = u'holger krekel'
epub_publisher = u'holger krekel'
epub_copyright = u'2010, holger krekel'

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
