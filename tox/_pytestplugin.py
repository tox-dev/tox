from __future__ import print_function

import os
import subprocess
import sys
import textwrap
import time
from fnmatch import fnmatch

import py
import pytest
import six

import tox
from .config import parseconfig
from .result import ResultLog
from .session import Action
from .venv import VirtualEnv


def pytest_configure():
    if 'TOXENV' in os.environ:
        del os.environ['TOXENV']
    if 'HUDSON_URL' in os.environ:
        del os.environ['HUDSON_URL']


def pytest_addoption(parser):
    parser.addoption("--no-network", action="store_true",
                     dest="no_network",
                     help="don't run tests requiring network")


def pytest_report_header():
    return "tox comes from: %r" % (tox.__file__)


@pytest.fixture
def newconfig(request, tmpdir):
    def newconfig(args, source=None, plugins=()):
        if source is None:
            source = args
            args = []
        s = textwrap.dedent(source)
        p = tmpdir.join("tox.ini")
        p.write(s)
        old = tmpdir.chdir()
        try:
            return parseconfig(args, plugins=plugins)
        finally:
            old.chdir()
    return newconfig


@pytest.fixture
def cmd(request):
    if request.config.option.no_network:
        pytest.skip("--no-network was specified, test cannot run")
    return Cmd(request)


class ReportExpectMock:
    def __init__(self, session):
        self._calls = []
        self._index = -1
        self.session = session

    def clear(self):
        self._calls[:] = []

    def __getattr__(self, name):
        if name[0] == "_":
            raise AttributeError(name)
        elif name == 'verbosity':
            # FIXME: special case for property on Reporter class, may it be generalized?
            return 0

        def generic_report(*args, **kwargs):
            self._calls.append((name,) + args)
            print("%s" % (self._calls[-1], ))
        return generic_report

    def action(self, venv, msg, *args):
        self._calls.append(("action", venv, msg))
        print("%s" % (self._calls[-1], ))
        return Action(self.session, venv, msg, args)

    def getnext(self, cat):
        __tracebackhide__ = True
        newindex = self._index + 1
        while newindex < len(self._calls):
            call = self._calls[newindex]
            lcat = call[0]
            if fnmatch(lcat, cat):
                self._index = newindex
                return call
            newindex += 1
        raise LookupError(
            "looking for %r, no reports found at >=%d in %r" %
            (cat, self._index + 1, self._calls))

    def expect(self, cat, messagepattern="*", invert=False):
        __tracebackhide__ = True
        if not messagepattern.startswith("*"):
            messagepattern = "*" + messagepattern
        while self._index < len(self._calls):
            try:
                call = self.getnext(cat)
            except LookupError:
                break
            for lmsg in call[1:]:
                lmsg = str(lmsg).replace("\n", " ")
                if fnmatch(lmsg, messagepattern):
                    if invert:
                        raise AssertionError("found %s(%r), didn't expect it" %
                                             (cat, messagepattern))
                    return
        if not invert:
            raise AssertionError(
                "looking for %s(%r), no reports found at >=%d in %r" %
                (cat, messagepattern, self._index + 1, self._calls))

    def not_expect(self, cat, messagepattern="*"):
        return self.expect(cat, messagepattern, invert=True)


class pcallMock:
    def __init__(self, args, cwd, env, stdout, stderr, shell):
        self.arg0 = args[0]
        self.args = args[1:]
        self.cwd = cwd
        self.env = env
        self.stdout = stdout
        self.stderr = stderr
        self.shell = shell

    def communicate(self):
        return "", ""

    def wait(self):
        pass


@pytest.fixture
def mocksession(request):
    from tox.session import Session

    class MockSession(Session):
        def __init__(self):
            self._clearmocks()
            self.config = request.getfixturevalue("newconfig")([], "")
            self.resultlog = ResultLog()
            self._actions = []

        def getenv(self, name):
            return VirtualEnv(self.config.envconfigs[name], session=self)

        def _clearmocks(self):
            self._pcalls = []
            self._spec2pkg = {}
            self.report = ReportExpectMock(self)

        def make_emptydir(self, path):
            pass

        def popen(self, args, cwd, shell=None,
                  universal_newlines=False,
                  stdout=None, stderr=None, env=None):
            pm = pcallMock(args, cwd, env, stdout, stderr, shell)
            self._pcalls.append(pm)
            return pm
    return MockSession()


@pytest.fixture
def newmocksession(request):
    mocksession = request.getfixturevalue("mocksession")
    newconfig = request.getfixturevalue("newconfig")

    def newmocksession(args, source, plugins=()):
        mocksession.config = newconfig(args, source, plugins=plugins)
        return mocksession
    return newmocksession


class Cmd:
    def __init__(self, request):
        self.tmpdir = request.getfixturevalue("tmpdir")
        self.request = request
        current = py.path.local()
        self.request.addfinalizer(current.chdir)

    def chdir(self, target):
        target.chdir()

    def popen(self, argv, stdout, stderr, **kw):
        env = os.environ.copy()
        env['PYTHONPATH'] = ":".join(filter(None, [
            str(os.getcwd()), env.get('PYTHONPATH', '')]))
        kw['env'] = env
        # print "env", env
        return subprocess.Popen(argv, stdout=stdout, stderr=stderr, **kw)

    def run(self, *argv):
        if argv[0] == "tox" and sys.version_info[:2] < (2, 7):
            pytest.skip("can not run tests involving calling tox on python2.6. "
                        "(and python2.6 is about to be deprecated anyway)")
        argv = [str(x) for x in argv]
        assert py.path.local.sysfind(str(argv[0])), argv[0]
        p1 = self.tmpdir.join("stdout")
        p2 = self.tmpdir.join("stderr")
        print("%s$ %s" % (os.getcwd(), " ".join(argv)))
        f1 = p1.open("wb")
        f2 = p2.open("wb")
        now = time.time()
        popen = self.popen(argv, stdout=f1, stderr=f2,
                           close_fds=(sys.platform != "win32"))
        ret = popen.wait()
        f1.close()
        f2.close()
        out = p1.read("rb")
        out = getdecoded(out).splitlines()
        err = p2.read("rb")
        err = getdecoded(err).splitlines()

        def dump_lines(lines, fp):
            try:
                for line in lines:
                    print(line, file=fp)
            except UnicodeEncodeError:
                print("couldn't print to %s because of encoding" % (fp,))
        dump_lines(out, sys.stdout)
        dump_lines(err, sys.stderr)
        return RunResult(ret, out, err, time.time() - now)


def getdecoded(out):
        try:
            return out.decode("utf-8")
        except UnicodeDecodeError:
            return "INTERNAL not-utf8-decodeable, truncated string:\n%s" % (
                py.io.saferepr(out),)


class RunResult:
    def __init__(self, ret, outlines, errlines, duration):
        self.ret = ret
        self.outlines = outlines
        self.errlines = errlines
        self.stdout = LineMatcher(outlines)
        self.stderr = LineMatcher(errlines)
        self.duration = duration


class LineMatcher:
    def __init__(self, lines):
        self.lines = lines

    def str(self):
        return "\n".join(self.lines)

    def fnmatch_lines(self, lines2):
        if isinstance(lines2, str):
            lines2 = py.code.Source(lines2)
        if isinstance(lines2, py.code.Source):
            lines2 = lines2.strip().lines

        from fnmatch import fnmatch
        lines1 = self.lines[:]
        nextline = None
        extralines = []
        __tracebackhide__ = True
        for line in lines2:
            nomatchprinted = False
            while lines1:
                nextline = lines1.pop(0)
                if line == nextline:
                    print("exact match:", repr(line))
                    break
                elif fnmatch(nextline, line):
                    print("fnmatch:", repr(line))
                    print("   with:", repr(nextline))
                    break
                else:
                    if not nomatchprinted:
                        print("nomatch:", repr(line))
                        nomatchprinted = True
                    print("    and:", repr(nextline))
                extralines.append(nextline)
            else:
                assert line == nextline


@pytest.fixture
def initproj(request, tmpdir):
    """ create a factory function for creating example projects. """
    def initproj(nameversion, filedefs=None, src_root="."):
        if filedefs is None:
            filedefs = {}
        if isinstance(nameversion, six.string_types):
            parts = nameversion.split("-")
            if len(parts) == 1:
                parts.append("0.1")
            name, version = parts
        else:
            name, version = nameversion
        base = tmpdir.ensure(name, dir=1)
        create_files(base, filedefs)
        if 'setup.py' not in filedefs:
            create_files(base, {'setup.py': '''
                from setuptools import setup, find_packages
                setup(
                    name='%(name)s',
                    description='%(name)s project',
                    version='%(version)s',
                    license='MIT',
                    platforms=['unix', 'win32'],
                    packages=find_packages('%(src_root)s'),
                    package_dir={'':'%(src_root)s'},
                )
            ''' % locals()})
        if name not in filedefs:
            src_dir = base.ensure(src_root, dir=1)
            create_files(src_dir, {
                name: {'__init__.py': '__version__ = %r' % version}
            })
        manifestlines = []
        for p in base.visit(lambda x: x.check(file=1)):
            manifestlines.append("include %s" % p.relto(base))
        create_files(base, {"MANIFEST.in": "\n".join(manifestlines)})
        print("created project in %s" % (base,))
        base.chdir()
    return initproj


def create_files(base, filedefs):
    for key, value in filedefs.items():
        if isinstance(value, dict):
            create_files(base.ensure(key, dir=1), value)
        elif isinstance(value, str):
            s = textwrap.dedent(value)
            base.join(key).write(s)
