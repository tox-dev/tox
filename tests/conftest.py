import py
import tox
import os
import sys
from py.builtin import print_
from fnmatch import fnmatch
import time
from tox._config import parseconfig

def pytest_configure():
    if 'TOXENV' in os.environ:
        del os.environ['TOXENV']
    if 'HUDSON_URL' in os.environ:
        del os.environ['HUDSON_URL']

def pytest_report_header():
    return "tox comes from: %r" % (tox.__file__)

def pytest_funcarg__newconfig(request):
    tmpdir = request.getfuncargvalue("tmpdir")
    def newconfig(args, source=None):
        if source is None:
            source = args
            args = []
        s = py.std.textwrap.dedent(source)
        p = tmpdir.join("tox.ini")
        p.write(s)
        old = tmpdir.chdir()
        try:
            return parseconfig(args)
        finally:
            old.chdir()
    return newconfig 

def pytest_funcarg__tmpdir(request):
    tmpdir = request.getfuncargvalue("tmpdir")
    request.addfinalizer(py.path.local().chdir)
    tmpdir.chdir()
    return tmpdir

def pytest_funcarg__cmd(request):
    return Cmd(request)

class ReportExpectMock:
    def __init__(self):
        self._calls = []
        self._index = -1

    def clear(self):
        self._calls[:] = []

    def __getattr__(self, name):
        if name[0] == "_":
            raise AttributeError(name)

        def generic_report(*args):
            self._calls.append((name,)+args)
            print ("report %s" %(args,))
        return generic_report

    def expect(self, cat, messagepattern):
        newindex = self._index + 1
        while newindex < len(self._calls):
            lcat, lmsg = self._calls[newindex]
            if lcat == cat and fnmatch(lmsg, messagepattern):
                self._index = newindex
                return
            newindex += 1
        raise AssertionError(
            "looking for %s(%r), no reports found at >=%d in %r" %
            (cat, messagepattern, self._index+1, self._calls))

class pcallMock:
    def __init__(self, args, log, cwd, env=None):
        self.args = args
        self.log = log
        self.cwd = cwd
        self.env = env
    
def pytest_funcarg__mocksession(request):
    from tox._cmdline import Session
    class MockSession(Session):
        def __init__(self):
            self._clearmocks()
        def _clearmocks(self):
            self._pcalls = []
            self.report = ReportExpectMock()
        def make_emptydir(self, path):
            pass
        def pcall(self, args, log, cwd, env=None):
            self._pcalls.append(pcallMock(args, log, cwd, env))
    return MockSession()

class Cmd:
    def __init__(self, request):
        self.tmpdir = request.getfuncargvalue("tmpdir")
        self.request = request
        current = py.path.local()
        self.request.addfinalizer(current.chdir)
    def chdir(self, target):
        target.chdir()

    def popen(self, argv, stdout, stderr, **kw):
        if not hasattr(py.std, 'subprocess'):
            py.test.skip("no subprocess module")
        env = os.environ.copy()
        env['PYTHONPATH'] = ":".join(filter(None, [
            str(os.getcwd()), env.get('PYTHONPATH', '')]))
        kw['env'] = env
        #print "env", env
        return py.std.subprocess.Popen(argv, stdout=stdout, stderr=stderr, **kw)

    def run(self, *argv):
        argv = [str(x) for x in argv]
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
                    py.builtin.print_(line, file=fp)
            except UnicodeEncodeError:
                print("couldn't print to %s because of encoding" % (fp,))
        dump_lines(out, sys.stdout)
        dump_lines(err, sys.stderr)
        return RunResult(ret, out, err, time.time()-now)

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
    def __init__(self,  lines):
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
                    print_("exact match:", repr(line))
                    break 
                elif fnmatch(nextline, line):
                    print_("fnmatch:", repr(line))
                    print_("   with:", repr(nextline))
                    break
                else:
                    if not nomatchprinted:
                        print_("nomatch:", repr(line))
                        nomatchprinted = True
                    print_("    and:", repr(nextline))
                extralines.append(nextline)
            else:
                assert line == nextline

def pytest_funcarg__initproj(request):
    """ create a factory function for creating example projects. """
    tmpdir = request.getfuncargvalue("tmpdir")
    def initproj(name, filedefs=None):
        if filedefs is None:
            filedefs = {}
        parts = name.split("-")
        if len(parts) == 1:
            parts.append("0.1")
        name, version = parts
        base = tmpdir.mkdir(name)
        create_files(base, filedefs)
        if 'setup.py' not in filedefs:
            create_files(base, {'setup.py': '''
                from setuptools import setup
                setup(
                    name='%(name)s',
                    description='%(name)s project', 
                    version='%(version)s',
                    license='GPLv2 or later',
                    platforms=['unix', 'win32'],
                    packages=['%(name)s', ],
                )
            ''' % locals()})
        if name not in filedefs:
            create_files(base, {name:
                {'__init__.py': '#'}})
        print ("created project in %s" %(base,))
        base.chdir()
    return initproj

def create_files(base, filedefs):
    for key, value in filedefs.items():
        if isinstance(value, dict):
            create_files(base.ensure(key, dir=1), value)
        elif isinstance(value, str):
            s = py.std.textwrap.dedent(value)
            base.join(key).write(s)
