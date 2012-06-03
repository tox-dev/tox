
import sys, os
import py
import tox
from tox._config import DepConfig

class CreationConfig:
    def __init__(self, md5, python, version, distribute, sitepackages, deps):
        self.md5 = md5
        self.python = python
        self.version = version
        self.distribute = distribute
        self.sitepackages = sitepackages
        self.deps = deps

    def writeconfig(self, path):
        lines = ["%s %s" % (self.md5, self.python)]
        lines.append("%s %d %d" % (self.version, self.distribute,
                        self.sitepackages))
        for dep in self.deps:
            lines.append("%s %s" % dep)
        path.ensure()
        path.write("\n".join(lines))

    @classmethod
    def readconfig(cls, path):
        try:
            lines = path.readlines(cr=0)
            value = lines.pop(0).split(None, 1)
            md5, python = value
            version, distribute, sitepackages = lines.pop(0).split(None, 2)
            distribute = bool(int(distribute))
            sitepackages = bool(int(sitepackages))
            deps = []
            for line in lines:
                md5, depstring = line.split(None, 1)
                deps.append((md5, depstring))
            return CreationConfig(md5, python, version,
                        distribute, sitepackages, deps)
        except KeyboardInterrupt:
            raise
        except:
            return None

    def matches(self, other):
        return (other and self.md5 == other.md5
           and self.python == other.python
           and self.version == other.version
           and self.distribute == other.distribute
           and self.sitepackages == other.sitepackages
           and self.deps == other.deps)

class VirtualEnv(object):
    def __init__(self, envconfig=None, session=None):
        self.envconfig = envconfig
        self.session = session
        self.path = envconfig.envdir
        self.path_config = self.path.join(".tox-config1")

    @property
    def name(self):
        return self.envconfig.envname

    def __repr__(self):
        return "<VirtualEnv at %r>" %(self.path)

    def getcommandpath(self, name=None):
        if name is None:
            return self.envconfig.envpython
        name = str(name)
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

    def update(self, action=None):
        """ return status string for updating actual venv to match configuration.
            if status string is empty, all is ok.
        """
        if action is None:
            action = self.session.newaction(self, "update")
        report = self.session.report
        name = self.envconfig.envname
        rconfig = CreationConfig.readconfig(self.path_config)
        if not self.envconfig.recreate and rconfig and \
            rconfig.matches(self._getliveconfig()):
            action.setactivity("reusing", "existing environment matches")
            return
        if rconfig is None:
            action.setactivity("create", "no existing environment found")
        else:
            action.setactivity("recreate",
                "configchange/incomplete install detected")
        try:
            self.create(action)
        except tox.exception.UnsupportedInterpreter:
            return sys.exc_info()[1]
        except tox.exception.InterpreterNotFound:
            return sys.exc_info()[1]
        try:
            self.install_deps(action)
        except tox.exception.InvocationError:
            v = sys.exc_info()[1]
            return "could not install deps %s" %(self.envconfig.deps,)

    def _getliveconfig(self):
        python = self.getconfigexecutable()
        md5 = getdigest(python)
        version = tox.__version__
        distribute = self.envconfig.distribute
        sitepackages = self.envconfig.sitepackages
        deps = []
        for dep in self._getresolvedeps():
            raw_dep = dep.name
            md5 = getdigest(raw_dep)
            deps.append((md5, raw_dep))
        return CreationConfig(md5, python, version,
                        distribute, sitepackages, deps)

    def _getresolvedeps(self):
        l = []
        for dep in self.envconfig.deps:
            if dep.indexserver is None:
                res = self.session._resolve_pkg(dep.name)
                if res != dep.name:
                    dep = dep.__class__(res)
            l.append(dep)
        return l

    def getconfigexecutable(self):
        python = self.envconfig.basepython
        if not python:
            python = sys.executable
        x = find_executable(str(python))
        if x:
            x = x.realpath()
        return x

    def getsupportedinterpreter(self):
        if sys.platform == "win32" and self.envconfig.basepython and \
                "jython" in self.envconfig.basepython:
            raise tox.exception.UnsupportedInterpreter(
                "Jython/Windows does not support installing scripts")
        config_executable = self.getconfigexecutable()
        if not config_executable:
            raise tox.exception.InterpreterNotFound(self.envconfig.basepython)
        return config_executable

    def create(self, action=None):
        #if self.getcommandpath("activate").dirpath().check():
        #    return
        if action is None:
            action = self.session.newaction(self, "create")
        config_interpreter = self.getsupportedinterpreter()
        f, path, _ = py.std.imp.find_module("virtualenv")
        f.close()
        venvscript = path.rstrip("co")
        #venvscript = py.path.local(tox.__file__).dirpath("virtualenv.py")
        args = [config_interpreter, venvscript]
        if not self._ispython3() and self.envconfig.distribute:
            args.append('--distribute')
        if self.envconfig.sitepackages:
            args.append('--system-site-packages')
        #if sys.platform == "win32":
        #    f, path, _ = py.std.imp.find_module("virtualenv")
        #    f.close()
        #    args[:1] = [str(config_interpreter), str(path)]
        #else:
        self.session.make_emptydir(self.path)
        basepath = self.path.dirpath()
        basepath.ensure(dir=1)
        old = py.path.local()
        try:
            basepath.chdir()
            args.append(self.path.basename)
            self._pcall(args, venv=False, action=action)
            #if self._ispython3():
            #    self.easy_install(["-U", "distribute"])
        finally:
            old.chdir()
        self.just_created = True

    def install_sdist(self, sdistpath):
        if getattr(self, 'just_created', False):
            action = self.session.newaction(self, "sdist-inst", sdistpath)
            self._getliveconfig().writeconfig(self.path_config)
            extraopts = []
        else:
            action = self.session.newaction(self, "sdist-reinst", sdistpath)
            extraopts = ['-U', '--no-deps']
        self._install([sdistpath], extraopts=extraopts, action=action)

    def install_deps(self, action=None):
        if action is None:
            action = self.session.newaction(self, "install_deps")
        deps = self._getresolvedeps()
        if deps:
            depinfo = ", ".join(map(str, deps))
            action.setactivity("installdeps",
                "%s" % depinfo)
            self._install(deps, action=action)

    def _commoninstallopts(self, indexserver):
        l = []
        if indexserver:
            l += ["-i", indexserver]
        return l

    def easy_install(self, args, indexserver=None):
        argv = ["easy_install"] + self._commoninstallopts(indexserver) + args
        self._pcall(argv, cwd=self.envconfig.envlogdir)

    def pip_install(self, args, indexserver=None, action=None):
        argv = ["pip", "install"] + self._commoninstallopts(indexserver)
        if self.envconfig.downloadcache:
            self.envconfig.downloadcache.ensure(dir=1)
            argv.append("--download-cache=%s" %
                self.envconfig.downloadcache)
        for x in ('PIP_RESPECT_VIRTUALENV', 'PIP_REQUIRE_VIRTUALENV'):
            try:
                del os.environ[x]
            except KeyError:
                pass
        argv += args
        env = dict(PYTHONIOENCODING='utf_8')
        self._pcall(argv, cwd=self.envconfig.envlogdir, extraenv=env,
            action=action)

    def _install(self, deps, extraopts=None, action=None):
        if not deps:
            return
        d = {}
        l = []
        for dep in deps:
            if isinstance(dep, (str, py.path.local)):
                dep = DepConfig(str(dep), None)
            assert isinstance(dep, DepConfig), dep
            if dep.indexserver is None:
                ixserver = self.envconfig.config.indexserver['default']
            else:
                ixserver = dep.indexserver
            url = ixserver.url
            d.setdefault(url, []).append(dep.name)
            if url not in l:
                l.append(url)
            assert url is None or isinstance(url, str)

        extraopts = extraopts or []
        for repo in l:
            args = d[repo] + extraopts
            self.pip_install(args, repo, action)

    def _getenv(self):
        env = self.envconfig.setenv
        if env:
            env_arg = os.environ.copy()
            env_arg.update(env)
        else:
            env_arg = None
        return env_arg

    def test(self, action=None, redirect=False):
        if action is None:
            action = self.session.newaction(self, "test")
        self.session.make_emptydir(self.envconfig.envtmpdir)
        cwd = self.envconfig.changedir
        for argv in self.envconfig.commands:
            try:
                self._pcall(argv, cwd=cwd, action=action, redirect=redirect)
            except tox.exception.InvocationError:
                self.session.report.error(str(sys.exc_info()[1]))
                return True

    def _pcall(self, args, venv=True, cwd=None, extraenv={},
            action=None, redirect=True):
        try:
            del os.environ['PYTHONDONTWRITEBYTECODE']
        except KeyError:
            pass
        if cwd:
            cwd.ensure(dir=1)

        old = self.patchPATH()
        try:
            args[0] = self.getcommandpath(args[0])
            if venv:
                if not py.path.local(args[0]).relto(self.envconfig.envdir):
                    self.session.report.warning(
                        "test command found but not installed in testenv\n"
                        "  cmd: %s\n"
                        "  env: %s\n"
                        "Maybe forgot to specify a dependency?" % (args[0],
                        self.envconfig.envdir))
            env = self._getenv() or os.environ.copy()
            env.update(extraenv)
            return action.popen(args, cwd=cwd, env=env, redirect=redirect)
        finally:
            os.environ['PATH'] = old

    def patchPATH(self):
        oldPATH = os.environ['PATH']
        bindir = str(self.envconfig.envbindir)
        os.environ['PATH'] = os.pathsep.join([bindir, oldPATH])
        return oldPATH

def getdigest(path):
    path = py.path.local(path)
    if not path.check(file=1):
        return "0" * 32
    return path.computehash()

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
