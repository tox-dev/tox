
import sys
import py
import tox

class VirtualEnv(object):
    def __init__(self, envconfig=None, session=None):
        self.envconfig = envconfig
        self.path = envconfig.envdir
        self.session = session

    def __repr__(self):
        return "<VirtualEnv at %r>" %(self.path)

    def getcommandpath(self, name=None):
        if name is None:
            if "jython" in str(self.envconfig.python):
                name = "jython"
            else:
                name = "python"
        if sys.platform == "win32":
            return self.path.join("Scripts", name)
        else:
            return self.path.join("bin", name)

    def _ispython3(self):
        return "python3" in str(self.envconfig.python)

    def create(self):
        #if self.getcommandpath("activate").dirpath().check():
        #    return 
        if sys.platform == "win32" and self._ispython3():
            raise MissingInterpreter("python3/virtualenv3 is buggy on windows")
        if sys.platform == "win32" and self.envconfig.python and \
                "jython" in self.envconfig.python:
            raise MissingInterpreter("Jython/Windows does not support installing scripts")
        args = ['virtualenv' + (self._ispython3() and "3" or "")]
        args.append('--no-site-packages')
        python = self.envconfig.python
        if not python:
            python = sys.executable
        p = find_executable(str(python))
        if not p:
            raise MissingInterpreter(self.envconfig.python)
        if sys.platform == "win32":
            f, path, _ = py.std.imp.find_module("virtualenv")
            f.close()
            args[:1] = [str(p), str(path)]
        else:
            args.extend(["-p", str(p)])
        basepath = self.path.dirpath()
        basepath.ensure(dir=1)
        old = py.path.local()
        try:
            basepath.chdir()
            args.append(self.path.basename)
            self._pcall(args, venv=False)
            if self._ispython3():
                self.install(["-U", "distribute"])
        finally:
            old.chdir()

    def install(self, deps):
        if not deps:
            return
        if self._ispython3():
            args = ["easy_install"] + deps
        else:
            args = ["pip", "install"] + deps
            if self.envconfig.downloadcache:
                self.envconfig.downloadcache.ensure(dir=1)
                args.append("--download-cache=%s" % 
                    self.envconfig.downloadcache)
        self._pcall(args)

    def test(self, cwd=None):
        envtmpdir = self.envconfig.envtmpdir
        self.session.make_emptydir(envtmpdir)
        try:
            self._pcall(self.envconfig.cmdargs, log=-1, cwd=cwd)
        except tox.exception.InvocationError:
            return True

    def _pcall(self, args, venv=True, log=None, cwd=None):
        if venv:
            args = [self.getcommandpath(args[0])] + args[1:]
        if log is None:
            log = self.path.ensure("log", dir=1)
        return self.session.pcall(args, log=log, cwd=cwd)

if sys.platform != "win32":
    def find_executable(name):
        return py.path.local.sysfind(name)

else:
    win32map = {
            'python': sys.executable,
            'python2.4': "c:\python24\python.exe",
            'python2.5': "c:\python25\python.exe",
            'python2.6': "c:\python26\python.exe",
            'python2.7': "c:\python27\python.exe",
            'python3.1': "c:\python31\python.exe",
            'jython': "c:\jython2.5.1\jython.bat",
    }
    def find_executable(name):
        p = py.path.local(name) 
        if p.check(file=1):
            return p
        actual = win32map.get(name, None)
        if actual:
            actual = py.path.local(actual)
            if actual.check():
                return actual


class MissingInterpreter(Exception):
    "signals an unknown or missing interpreter"
