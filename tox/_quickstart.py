# -*- coding: utf-8 -*-
"""
    tox._quickstart
    ~~~~~~~~~~~~~~~~~

    Command-line script to quickly setup tox.ini for a Python project

    This file was heavily inspired by and uses code from ``sphinx-quickstart``
    in the BSD-licensed `Sphinx project`_.

    .. Sphinx project_: http://sphinx.pocoo.org/

    License for Sphinx
    ==================

    Copyright (c) 2007-2011 by the Sphinx team (see AUTHORS file).
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are
    met:

    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.

    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
    "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
    LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
    A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
    OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
    LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
    DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
    THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
    (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
    OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
from os import path
from codecs import open

TERM_ENCODING = getattr(sys.stdin, 'encoding', None)

from tox import __version__

# function to get input from terminal -- overridden by the test suite
try:
    # this raw_input is not converted by 2to3
    term_input = raw_input
except NameError:
    term_input = input


all_envs = ['py26', 'py27', 'py32', 'py33', 'py34', 'py35', 'pypy', 'jython']

PROMPT_PREFIX = '> '

QUICKSTART_CONF = '''\
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = %(envlist)s

[testenv]
commands = %(commands)s
deps = %(deps)s
'''


class ValidationError(Exception):
    """Raised for validation errors."""


def nonempty(x):
    if not x:
        raise ValidationError("Please enter some text.")
    return x


def choice(*l):
    def val(x):
        if x not in l:
            raise ValidationError('Please enter one of %s.' % ', '.join(l))
        return x
    return val


def boolean(x):
    if x.upper() not in ('Y', 'YES', 'N', 'NO'):
        raise ValidationError("Please enter either 'y' or 'n'.")
    return x.upper() in ('Y', 'YES')


def suffix(x):
    if not (x[0:1] == '.' and len(x) > 1):
        raise ValidationError("Please enter a file suffix, "
                              "e.g. '.rst' or '.txt'.")
    return x


def ok(x):
    return x


def do_prompt(d, key, text, default=None, validator=nonempty):
    while True:
        if default:
            prompt = PROMPT_PREFIX + '%s [%s]: ' % (text, default)
        else:
            prompt = PROMPT_PREFIX + text + ': '
        x = term_input(prompt)
        if default and not x:
            x = default
        if sys.version_info < (3, ) and not isinstance(x, unicode):
            # for Python 2.x, try to get a Unicode string out of it
            if x.decode('ascii', 'replace').encode('ascii', 'replace') != x:
                if TERM_ENCODING:
                    x = x.decode(TERM_ENCODING)
                else:
                    print('* Note: non-ASCII characters entered '
                          'and terminal encoding unknown -- assuming '
                          'UTF-8 or Latin-1.')
                    try:
                        x = x.decode('utf-8')
                    except UnicodeDecodeError:
                        x = x.decode('latin1')
        try:
            x = validator(x)
        except ValidationError:
            err = sys.exc_info()[1]
            print('* ' + str(err))
            continue
        break
    d[key] = x


def ask_user(d):
    """Ask the user for quickstart values missing from *d*.

    """

    print('Welcome to the Tox %s quickstart utility.' % __version__)
    print('''
This utility will ask you a few questions and then generate a simple tox.ini
file to help get you started using tox.

Please enter values for the following settings (just press Enter to
accept a default value, if one is given in brackets).''')

    sys.stdout.write('\n')

    print('''
What Python versions do you want to test against? Choices:
    [1] py27
    [2] py27, py33
    [3] (All versions) %s
    [4] Choose each one-by-one''' % ', '.join(all_envs))
    do_prompt(d, 'canned_pyenvs', 'Enter the number of your choice',
              '3', choice('1', '2', '3', '4'))

    if d['canned_pyenvs'] == '1':
        d['py27'] = True
    elif d['canned_pyenvs'] == '2':
        for pyenv in ('py27', 'py33'):
            d[pyenv] = True
    elif d['canned_pyenvs'] == '3':
        for pyenv in all_envs:
            d[pyenv] = True
    elif d['canned_pyenvs'] == '4':
        for pyenv in all_envs:
            if pyenv not in d:
                do_prompt(d, pyenv, 'Test your project with %s (Y/n)' % pyenv, 'Y', boolean)

    print('''
What command should be used to test your project -- examples:
    - py.test
    - python setup.py test
    - nosetests package.module
    - trial package.module''')
    do_prompt(d, 'commands', 'Command to run to test project', '{envpython} setup.py test')

    default_deps = ' '
    if 'py.test' in d['commands']:
        default_deps = 'pytest'
    if 'nosetests' in d['commands']:
        default_deps = 'nose'
    if 'trial' in d['commands']:
        default_deps = 'twisted'

    print('''
What extra dependencies do your tests have?''')
    do_prompt(d, 'deps', 'Comma-separated list of dependencies', default_deps)


def process_input(d):
    d['envlist'] = ', '.join([env for env in all_envs if d.get(env) is True])
    d['deps'] = '\n' + '\n'.join([
        '    %s' % dep.strip()
        for dep in d['deps'].split(',')])

    return d


def rtrim_right(text):
    lines = []
    for line in text.split("\n"):
        lines.append(line.rstrip())
    return "\n".join(lines)


def generate(d, overwrite=True, silent=False):
    """Generate project based on values in *d*."""

    conf_text = QUICKSTART_CONF % d
    conf_text = rtrim_right(conf_text)

    def write_file(fpath, mode, content):
        print('Creating file %s.' % fpath)
        f = open(fpath, mode, encoding='utf-8')
        try:
            f.write(content)
        finally:
            f.close()

    sys.stdout.write('\n')

    fpath = 'tox.ini'

    if path.isfile(fpath) and not overwrite:
        print('File %s already exists.' % fpath)
        do_prompt(d, 'fpath', 'Alternative path to write tox.ini contents to', 'tox-generated.ini')
        fpath = d['fpath']

    write_file(fpath, 'w', conf_text)

    if silent:
        return
    sys.stdout.write('\n')
    print('Finished: A tox.ini file has been created. For information on this file, '
          'see http://tox.testrun.org/latest/config.html')
    print('''
Execute `tox` to test your project.
''')


def main(argv=sys.argv):
    d = {}

    if len(argv) > 3:
        print('Usage: tox-quickstart [root]')
        sys.exit(1)
    elif len(argv) == 2:
        d['path'] = argv[1]

    try:
        ask_user(d)
    except (KeyboardInterrupt, EOFError):
        print()
        print('[Interrupted.]')
        return

    d = process_input(d)
    generate(d, overwrite=False)


if __name__ == '__main__':
    main()
