
import sys
import py
import tox

class VirtualEnv(object):
    def __init__(self, envconfig=None, project=None):
        self.envconfig = envconfig
        self.path = envconfig.envdir
        self.project = project

    def __repr__(self):
        return "<VirtualEnv at %r>" %(self.path)

    def getcommandpath(self, name=None):
        if name is None:
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
        args = ['virtualenv' + (self._ispython3() and "3" or "")]
        args.append('--no-site-packages')
        if self.envconfig.python:
            args.append('-p')
            args.append(str(self.envconfig.python))
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
        cmd = self.envconfig.command % {'envname': self.envconfig.name}
        try:
            self._pcall(cmd.split(" "), out="passthrough", cwd=cwd)
        except tox.exception.InvocationError:
            return True

    def _pcall(self, args, venv=True, out=None, cwd=None):
        if venv:
            args = [self.getcommandpath(args[0])] + args[1:]
        return self.project.pcall(args, out=out, cwd=cwd)

def find_executable(name):
    p = py.path.local(name) 
    if p.check():
        return p
    p = py.path.local.sysfind(name)
    if p is not None:
        return p

