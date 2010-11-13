#!/usr/bin/env python
# The MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
tox-bootstrap
=============

A bootstrap to automatically install tox and dependencies on machines that may
not already have tox installed. This is useful when configuring a number of
Hudson quickly; only Python needs to be installed.

Getting started
---------------

::

    $ cd my_project/
    $ ls
    . .. src/ doc/ setup.py tox.ini
    $ curl http://pytox.googlecode.com/hg/toxbootstrap.py -O

Instead of running "tox", now you can just run "python toxbootstrap.py" which
will take care of installing tox (if not already installed into
``.tox/_toxinstall``)::

    $ python toxbootstrap.py

If you're using Hudson_, you may also do::

    import sys
    sys.path.insert(0, '.') # sometimes necessary :/
    import toxbootstrap
    toxbootstrap.cmdline() # also accepts argv list

.. _Hudson: http://hudson-ci.org/

ToDo
----

1. Detect tox in ``$PATH`` (eg: ``C:\Python26\Scripts`` or
   ``%APPDATA%\Python\Scripts``)

2. Gracefully ignore PyPI xmlrpc downtime errors when checking for new release.

"""

__version__ = '0.9.dev8'

import sys
import os
from os import path
import logging

from subprocess import Popen, PIPE, check_call, CalledProcessError

USETOXDEV=os.environ.get('USETOXDEV', False)
TENV='_toxinstall'

PY3 = sys.version_info[0] == 3

if PY3:
    from urllib.request import urlretrieve
    import xmlrpc.client as xmlrpclib
else:
    from urllib import urlretrieve
    import xmlrpclib

logging.basicConfig(level=logging.INFO)


# Last stable: 1.5.1
VIRTUALENVPY_URL = (
    'http://bitbucket.org/ianb/virtualenv/raw/eb94c9ebe0ba/virtualenv.py')

def run(cmd, shell=True):
    """Run the given command in shell"""
    logging.info('Running command: %s', cmd)
    check_call(cmd, shell=shell)


def crun(cmd, shell=True):
    """Run the given command and return its output"""
    logging.info('Running command (for output): %s', cmd)
    p = Popen(cmd, stdout=PIPE, shell=shell)
    stdout, stderr = p.communicate()
    return stdout


def wget(url):
    """Download the given file to current directory"""
    logging.info('Downloading %s', url)
    localpath = path.join(path.abspath(os.getcwd()), path.basename(url))
    urlretrieve(url, localpath)


def has_script(venv, name):
    """Check if the virtualenv has the given script

    Looks for bin/$name (unix) or Scripts/$name.exe (windows) in the virtualenv
    """
    if sys.platform == 'win32':
        return any([path.exists(path.join(venv, 'Scripts', name)),
                    path.exists(path.join(venv, 'Scripts', name + '.exe'))])
    else:
        return path.exists(path.join(venv, 'bin', name))


def get_script_path(venv, name):
    """Return the full path to the script in virtualenv directory"""
    if sys.platform == 'win32':
        p = path.join(venv, 'Scripts', name)
        if not path.exists(p):
            p = path.join(venv, 'Scripts', name + '.exe')
    else:
        p = path.join(venv, 'bin', name)

    if not path.exists(p):
        raise NameError('cannot find a script named "%s"' % (name,))

    return p


def get_tox_version(venv):
    """Return the installed version of tox"""
    py = get_script_path(venv, 'python')
    s = 'import tox,sys; sys.stdout.write(str(tox.__version__))'
    if sys.version_info[:2] >= (2, 6):
        return crun('%s -s -c "%s"' % (py, s))
    else:
        return crun('%s -c "%s"' % (py, s))


def parse_simple_version(v):
    """A simplified version of pkg_resources.parse_version

    This method can only parse simple versions like the ones with a set of
    numbers separated by dots (eg: 1.2.3)
    """
    return [int(c) for c in v.split('.')]


def pypi_get_latest_version(pkgname):
    """Return the latest version of package from PyPI"""
    pypi = xmlrpclib.ServerProxy('http://pypi.python.org/pypi')
    versions = pypi.package_releases('tox')
    assert versions
    versions.sort(key=parse_simple_version, reverse=True)
    return versions[0]

def ensuredir(p):
    if not path.isdir(p):
        os.makedirs(p)

def cmdline(argv=None):
    currentdir = os.getcwd()
    #os.chdir(path.abspath(path.dirname(__file__)))
    ensuredir('.tox')
    os.chdir('.tox')

    os.environ['PATH'] = os.path.abspath(TENV) + os.path.pathsep + os.environ['PATH']
    # create virtual environment
    if not path.isdir(TENV) or not has_script(TENV, 'python') or \
        not has_script(TENV, 'pip'):
        # get virtualenv.py
        if not path.isfile('virtualenv.py'):
            wget(VIRTUALENVPY_URL)
        assert path.isfile('virtualenv.py')

        # XXX: we use --no-site-packages because: if tox is installed in global
        # site-packages, then pip will not install it locally. ideal fix for
        # this should be to first look for tox in the global scripts/ directory
        run('%s virtualenv.py --no-site-packages --distribute %s' %
                (sys.executable, TENV))

    assert has_script(TENV, 'python'), 'no python script'
    assert has_script(TENV, 'pip'), 'no pip script'

    pip = get_script_path(TENV, 'pip')

    # install/upgrade tox itself
    if USETOXDEV:
        if 'PIP_DOWNLOAD_CACHE' in os.environ:
            cache = ""
        else:
            cache = "--download-cache=_download"
            ensuredir('_download')
        run('%s install -q -i http://pypi.testrun.org '
            '--upgrade %s tox' % (pip, cache))
    elif any([
        not has_script(TENV, 'tox'),
        get_tox_version(TENV) != pypi_get_latest_version('tox')]):
        run('%s install --upgrade --download-cache=_download tox' % (pip,))

    assert has_script(TENV, 'tox')
    tox_script = path.abspath(get_script_path(TENV, 'tox'))
    logging.info('tox is already installed at %s', tox_script)

    virtualenv = get_script_path(TENV, 'virtualenv')

    # XXX: virtualenv 1.5 is broken; replace it
    if crun('%s --version' % (virtualenv,)).strip() == '1.5':
        logging.info(
            'Replacing the unstable virtualenv-1.5 with the latest stable')
        run('%s uninstall -y virtualenv' % (pip,))
        run('%s install virtualenv!=1.5' % (pip,))

    # Now run the locally-installed tox
    os.chdir(currentdir)
    try:
        run([tox_script] + (argv or []), shell=False)
    except CalledProcessError:
        _, e, _ = sys.exc_info()
        logging.error('tox exited with error code %d', e.returncode)
        sys.exit(e.returncode)


if __name__ == '__main__':
    cmdline(sys.argv[1:])
