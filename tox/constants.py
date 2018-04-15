"""All non private names (no leading underscore) here are part of the tox API.

They live in the tox namespace and can be accessed as tox.[NAMESPACE.]NAME
"""
import sys as _sys


class PYTHON:
    CPYTHON_VERSION_TUPLES = [(2, 7), (3, 4), (3, 5), (3, 6), (3, 7)]
    OTHER_PYTHON_INTERPRETERS = ['jython', 'pypy', 'pypy3']
    _map = {'py': _sys.executable, 'py2': 'python2', 'py3': 'python3'}
    _map.update({'py%s%s' % (major, minor): 'python%s.%s' % (major, minor)
                 for major, minor in CPYTHON_VERSION_TUPLES})
    _map.update({interpreter: interpreter for interpreter in OTHER_PYTHON_INTERPRETERS})
    DEFAULT_FACTORS = _map


class INFO:
    IS_WIN = _sys.platform == "win32"


class PIP:
    SHORT_OPTIONS = ['c', 'e', 'r', 'b', 't', 'd']
    LONG_OPTIONS = [
        'build',
        'cache-dir',
        'client-cert',
        'constraint',
        'download',
        'editable',
        'exists-action',
        'extra-index-url',
        'global-option',
        'find-links',
        'index-url',
        'install-options',
        'prefix',
        'proxy',
        'no-binary',
        'only-binary',
        'requirement',
        'retries',
        'root',
        'src',
        'target',
        'timeout',
        'trusted-host',
        'upgrade-strategy',
    ]
    INSTALL_SHORT_OPTIONS_ARGUMENT = ['-%s' % option for option in SHORT_OPTIONS]
    INSTALL_LONG_OPTIONS_ARGUMENT = ['--%s' % option for option in LONG_OPTIONS]
