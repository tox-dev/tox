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

A bootstrap script to automatically install tox on machines that do not already
have it.  This is especially useful when configuring a number of Jenkins slaves
quickly (see `zero installation for slaves
<http://tox.testrun.org/latest/example/jenkins.html#zero-installation-for-slaves>>`
in tox documentation); only Python needs to be pre-installed.

Getting started
---------------

::

    $ cd my_project/
    $ ls
    . .. src/ doc/ setup.py tox.ini
    $ curl https://bitbucket.org/hpk42/tox/raw/default/toxbootstrap.py

Instead of running "tox", now you can just run "python toxbootstrap.py" which
will take care of installing tox (if not already installed into
``.tox/_toxinstall``)::

    $ python toxbootstrap.py

Note that, when configuring Jenkins slaves, you need not add `toxbootstrap.py` to
your source tree; see the above linked Jenkins configuration example in tox
documentation.

ToDo
----

1. Detect tox in ``$PATH`` (eg: ``C:\Python26\Scripts`` or
   ``%APPDATA%\Python\Scripts``)

2. Gracefully ignore PyPI xmlrpc downtime errors when checking for new release.

"""

__version__ = '1.5.dev9'

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


# Last stable: 1.6 (now on github)
VIRTUALENVPY_URL = ('https://github.com/pypa/virtualenv/raw/master/virtualenv.py')

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

def activate_path(venv):
    """Return the full path to the script virtualenv directory"""
    if sys.platform == 'win32':
        p = path.abspath(path.join(venv, 'Scripts'))
    else:
        p = path.abspath(path.join(venv, 'bin'))
    assert path.exists(p), p
    os.environ['PATH'] = p + os.pathsep + os.environ['PATH']
    logging.info("added to PATH: %s", p)

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
    logging.info('toxbootstrap version %s', __version__)
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
        logging.info("removing virtualenv.py script after bootstrap venv creation")
        for x in ('', 'o', 'c'):
            try:
                os.remove("virtualenv.py%s" % x)
            except OSError:
                pass

    assert has_script(TENV, 'python'), 'no python script'
    assert has_script(TENV, 'pip'), 'no pip script'
    activate_path(TENV)

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

    toxversion = get_tox_version(TENV)
    assert has_script(TENV, 'tox')
    tox_script = path.abspath(get_script_path(TENV, 'tox'))
    logging.info('tox is installed at %s version %s', tox_script, toxversion)

    #virtualenv = get_script_path(TENV, 'virtualenv')
    #venv_version = crun('%s --version' % (virtualenv,)).strip()
    #logging.info('virtualenv at %s version %s', virtualenv, venv_version)

    # XXX: virtualenv 1.5 is broken; replace it
    #if venv_version == '1.5':
    #    logging.info(
    #        'Replacing the unstable virtualenv-1.5 with the latest stable')
    #    run('%s uninstall -y virtualenv' % (pip,))
    #    run('%s install virtualenv!=1.5' % (pip,))

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
