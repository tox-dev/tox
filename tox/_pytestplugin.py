from __future__ import print_function
from __future__ import unicode_literals

import os
import textwrap
import time
from fnmatch import fnmatch

import py
import pytest
import six

import tox
from .config import parseconfig
from .result import ResultLog
from .session import main
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
    return "tox comes from: {}".format(repr(tox.__file__))


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
def cmd(request, capfd, monkeypatch):
    if request.config.option.no_network:
        pytest.skip("--no-network was specified, test cannot run")
    request.addfinalizer(py.path.local().chdir)

    def run(*argv):
        key = str(b'PYTHONPATH')
        python_paths = (i for i in (str(os.getcwd()), os.getenv(key)) if i)
        monkeypatch.setenv(key, os.pathsep.join(python_paths))
        with RunResult(capfd, argv) as result:
            try:
                main([str(x) for x in argv])
                assert False  # this should always exist with SystemExit
            except SystemExit as exception:
                result.ret = exception.code
            except OSError as e:
                result.ret = e.errno
        return result

    yield run


class RunResult:
    def __init__(self, capfd, args):
        self._capfd = capfd
        self.args = args
        self.ret = None
        self.duration = None
        self.out = None
        self.err = None

    def __enter__(self):
        self._start = time.time()
        # noinspection PyProtectedMember
        self._capfd._start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self._start
        self.out, self.err = self._capfd.readouterr()

    @property
    def outlines(self):
        return self.out.splitlines()

    def __repr__(self):
        return 'RunResult(ret={}, args={}, out=\n{}\n, err=\n{})'.format(
            self.ret, ' '.join(str(i) for i in self.args), self.out, self.err)


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
            print("%s" % (self._calls[-1],))

        return generic_report

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


def getdecoded(out):
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return "INTERNAL not-utf8-decodeable, truncated string:\n%s" % (
            py.io.saferepr(out),)


@pytest.fixture
def initproj(request, tmpdir):
    """Create a factory function for creating example projects

    Constructed folder/file hierarchy examples:

    with `src_root` other than `.`:

      tmpdir/
          name/                  # base
            src_root/            # src_root
                name/            # package_dir
                    __init__.py
                name.egg-info/   # created later on package build
            setup.py

    with `src_root` given as `.`:

      tmpdir/
          name/                  # base, src_root
            name/                # package_dir
                __init__.py
            name.egg-info/       # created later on package build
            setup.py

    """

    def initproj(nameversion, filedefs=None, src_root="."):
        if filedefs is None:
            filedefs = {}
        if not src_root:
            src_root = '.'
        if isinstance(nameversion, six.string_types):
            parts = nameversion.split(str("-"))
            if len(parts) == 1:
                parts.append("0.1")
            name, version = parts
        else:
            name, version = nameversion

        base = tmpdir.join(name)
        src_root_path = _path_join(base, src_root)
        assert base == src_root_path or src_root_path.relto(base), (
            '`src_root` must be the constructed project folder or its direct '
            'or indirect subfolder')

        base.ensure(dir=1)
        create_files(base, filedefs)

        if not _filedefs_contains(base, filedefs, 'setup.py'):
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

        if not _filedefs_contains(base, filedefs, src_root_path.join(name)):
            create_files(src_root_path, {
                name: {'__init__.py': '__version__ = %r' % version}
            })

        manifestlines = ["include %s" % p.relto(base)
                         for p in base.visit(lambda x: x.check(file=1))]
        create_files(base, {"MANIFEST.in": "\n".join(manifestlines)})

        print("created project in %s" % (base,))
        base.chdir()
        return base

    return initproj


def _path_parts(path):
    path = path and str(path)  # py.path.local support
    parts = []
    while path:
        folder, name = os.path.split(path)
        if folder == path:  # root folder
            folder, name = name, folder
        if name:
            parts.append(name)
        path = folder
    parts.reverse()
    return parts


def _path_join(base, *args):
    # workaround for a py.path.local bug on Windows (`path.join('/x', abs=1)`
    # should be py.path.local('X:\\x') where `X` is the current drive, when in
    # fact it comes out as py.path.local('\\x'))
    return py.path.local(base.join(*args, abs=1))


def _filedefs_contains(base, filedefs, path):
    """
    whether `filedefs` defines a file/folder with the given `path`

    `path`, if relative, will be interpreted relative to the `base` folder, and
    whether relative or not, must refer to either the `base` folder or one of
    its direct or indirect children. The base folder itself is considered
    created if the filedefs structure is not empty.

    """
    unknown = object()
    base = py.path.local(base)
    path = _path_join(base, path)

    path_rel_parts = _path_parts(path.relto(base))
    for part in path_rel_parts:
        if not isinstance(filedefs, dict):
            return False
        filedefs = filedefs.get(part, unknown)
        if filedefs is unknown:
            return False
    return path_rel_parts or path == base and filedefs


def create_files(base, filedefs):
    for key, value in filedefs.items():
        if isinstance(value, dict):
            create_files(base.ensure(key, dir=1), value)
        elif isinstance(value, six.string_types):
            s = textwrap.dedent(value)
            base.join(key).write(s)
