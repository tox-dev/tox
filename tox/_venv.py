
import sys, os
import py
import tox

class VirtualEnv(object):
    def __init__(self, envconfig=None, session=None):
        self.envconfig = envconfig
        self.session = session
        self.path = envconfig.envdir
        self.path_deps = self.path.join(".tox-deps")
        self.path_python = self.path.join(".tox-python")

    def __repr__(self):
        return "<VirtualEnv at %r>" %(self.path)

    def getcommandpath(self, name=None):
        if name is None:
            return self.envconfig.envpython
        if os.path.isabs(name):
            return name
        p = py.path.local.sysfind(name)
        if p is None:
            raise tox.exception.InvocationError("could not find executable %r" 
                % (name,))
        if p.relto(self.envconfig.envdir):
            return p
        return str(p) # will not be rewritten for reporting

    def _ispython3(self):
        return "python3" in str(self.envconfig.basepython)

    def update(self):
        """ return status string for updating actual venv to match configuration. 
            if status string is empty, all is ok.  
        """
        report = self.session.report
        name = self.envconfig.envname 
        if not self.iscorrectpythonenv():
            if not self.path_python.check():
                report.action("creating virtualenv %s" % name)
            else:
                report.action("recreating virtualenv %s "
                    "(configchange/partial install detected)" % name)
            try:
                self.create()
            except tox.exception.UnsupportedInterpreter:
                return sys.exc_info()[1]
            except tox.exception.InterpreterNotFound:
                return sys.exc_info()[1]
            try:
                self.install_deps()
            except tox.exception.InvocationError:
                v = sys.exc_info()[1]
                return "could not install deps %r" %(
                        ",".join(self.envconfig.deps))
        else:
            report.action("reusing existing matching virtualenv %s" %
                (self.envconfig.envname,))

    def iscorrectpythonenv(self):
        if self.path_python.check():
            s = self.path_python.read()
            executable = self.getconfigexecutable()
            if s == executable:
                return self.matchingdependencies()
        return False

    def _getconfigdeps(self):
        return [self.session._resolve_pkg(dep) for dep in self.envconfig.deps]

    def matchingdependencies(self):
        if self.path_deps.check():
            configdeps = self._getconfigdeps()
            for depline in self.path_deps.readlines(cr=0):
                depline = depline.strip()
                if not depline:
                    continue
                parts = depline.rsplit(" ", 1)
                if len(parts) > 1:
                    dep, digest = parts
                    if dep not in configdeps:
                        return False
                    path = py.path.local(dep)
                    if not path.check() or getdigest(path) != digest:
                        return False
                else:
                    dep = depline
                    if dep not in configdeps:
                        return False
                configdeps.remove(dep)
            if not configdeps: # no deps left
                return True
        return False

    def _writedeps(self, deps):
        lines = []
        for dep in deps:
            path = py.path.local(dep)
            if path.check():
                depline = "%s %s" %(dep, getdigest(path))
            else:
                depline = dep
            lines.append(depline)
        self.path_deps.write("\n".join(lines))

    def getconfigexecutable(self):
        python = self.envconfig.basepython
        if not python:
            python = sys.executable
        x = find_executable(str(python))
        if x:
            x = x.realpath()
        return x

    def getsupportedinterpreter(self):
        if sys.platform == "win32" and self._ispython3():
            raise tox.exception.UnsupportedInterpreter(
                "python3/virtualenv3 is buggy on windows")
        if sys.platform == "win32" and self.envconfig.basepython and \
                "jython" in self.envconfig.basepython:
            raise tox.exception.UnsupportedInterpreter(
                "Jython/Windows does not support installing scripts")
        config_executable = self.getconfigexecutable()
        if not config_executable:
            raise tox.exception.InterpreterNotFound(self.envconfig.basepython)
        return config_executable

    def create(self):
        #if self.getcommandpath("activate").dirpath().check():
        #    return 
        config_interpreter = self.getsupportedinterpreter()
        args = ['virtualenv' + (self._ispython3() and "3" or "")]
        args.append('--no-site-packages')
        if not self._ispython3() and self.envconfig.distribute:
            args.append('--distribute')
        if sys.platform == "win32":
            f, path, _ = py.std.imp.find_module("virtualenv")
            f.close()
            args[:1] = [str(config_interpreter), str(path)]
        else:
            args.extend(["-p", str(config_interpreter)])
        self.session.make_emptydir(self.path)
        basepath = self.path.dirpath()
        basepath.ensure(dir=1)
        old = py.path.local()
        try:
            basepath.chdir()
            args.append(self.path.basename)
            self._pcall(args, venv=False)
            if self._ispython3():
                self.easy_install(["-U", "distribute"])
        finally:
            old.chdir()
        self.path_python.write(str(config_interpreter))

    def install_sdist(self, sdistpath):
        self._install([sdistpath])

    def install_deps(self):
        deps = self._getconfigdeps()
        self.session.report.action("installing dependencies %s" %(deps))
        self._install(deps)
        self._writedeps(deps)

    def easy_install(self, args):
        argv = ["easy_install"] + args
        self._pcall(argv)

    def pip_install(self, args):
        argv = ["pip", "install"] + args
        if self.envconfig.downloadcache:
            self.envconfig.downloadcache.ensure(dir=1)
            argv.append("--download-cache=%s" % 
                self.envconfig.downloadcache)
        self._pcall(argv)

    def _install(self, args):
        if not args:
            return
        if self._ispython3():
            self.easy_install(args)
        else:
            self.pip_install(args)

    def test(self):
        self.session.make_emptydir(self.envconfig.envtmpdir)
        cwd = self.envconfig.changedir
        for argv in self.envconfig.commands:
            try:
                self._pcall(argv, log=-1, cwd=cwd)
            except tox.exception.InvocationError:
                return True

    def _pcall(self, args, venv=True, log=None, cwd=None):
        old = self.patchPATH()
        try:
            if venv:
                args = [self.getcommandpath(args[0])] + args[1:]
            if log is None:
                log = self.path.ensure("log", dir=1)
            return self.session.pcall(args, log=log, cwd=cwd)
        finally:
            os.environ['PATH'] = old

    def patchPATH(self):
        oldPATH = os.environ['PATH']
        paths = oldPATH.split(os.pathsep)
        bindir = str(self.envconfig.envbindir)
        if bindir not in paths:
            paths.insert(0, bindir)
            os.environ['PATH'] = x = os.pathsep.join(paths)
            self.session.report.info("added %r to path" % str(bindir))
        return oldPATH

def getdigest(path):
    try:
        from hashlib import md5
    except ImportError:
        from md5 import md5
    f = path.open("rb")
    s = f.read()
    f.close()
    return md5(s).hexdigest()

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
            'python3.2': "c:\python32\python.exe",
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


