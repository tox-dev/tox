from __future__ import with_statement
import sys, os
import codecs
import py
import tox
from tox._config import DepConfig

class CreationConfig:
    def __init__(self, md5, python, version, distribute, sitepackages,
                 develop, deps):
        self.md5 = md5
        self.python = python
        self.version = version
        self.distribute = distribute
        self.sitepackages = sitepackages
        self.develop = develop
        self.deps = deps

    def writeconfig(self, path):
        lines = ["%s %s" % (self.md5, self.python)]
        lines.append("%s %d %d %d" % (self.version, self.distribute,
                        self.sitepackages, self.develop))
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
            version, distribute, sitepackages, develop = lines.pop(0).split(
                None, 3)
            distribute = bool(int(distribute))
            sitepackages = bool(int(sitepackages))
            develop = bool(int(develop))
            deps = []
            for line in lines:
                md5, depstring = line.split(None, 1)
                deps.append((md5, depstring))
            return CreationConfig(md5, python, version,
                        distribute, sitepackages, develop, deps)
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
           and self.develop == other.develop
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

    def getcommandpath(self, name=None, venv=True, cwd=None):
        if name is None:
            return self.envconfig.envpython
        name = str(name)
        if os.path.isabs(name):
            return name
        if os.path.split(name)[0] == ".":
            p = cwd.join(name)
            if p.check():
                return str(p)
        p = None
        if venv:
            p = py.path.local.sysfind(name, paths=[self.envconfig.envbindir])
        if p is not None:
            return p
        p = py.path.local.sysfind(name)
        if p is None:
            raise tox.exception.InvocationError(
                    "could not find executable %r" % (name,))
        # p is not found in virtualenv script/bin dir
        if venv:
            if not self.is_allowed_external(p):
                self.session.report.warning(
                    "test command found but not installed in testenv\n"
                    "  cmd: %s\n"
                    "  env: %s\n"
                    "Maybe forgot to specify a dependency?" % (p,
                    self.envconfig.envdir))
        return str(p) # will not be rewritten for reporting

    def is_allowed_external(self, p):
        tryadd = [""]
        if sys.platform == "win32":
            tryadd += [os.path.normcase(x)
                        for x in os.environ['PATHEXT'].split(os.pathsep)]
            p = py.path.local(os.path.normcase(str(p)))
        for x in self.envconfig.whitelist_externals:
            for add in tryadd:
                if p.fnmatch(x + add):
                    return True
        return False

    def _ispython3(self):
        return "python3" in str(self.envconfig.basepython)

    def update(self, action=None):
        """ return status string for updating actual venv to match configuration.
            if status string is empty, all is ok.
        """
        if action is None:
            action = self.session.newaction(self, "update")
        rconfig = CreationConfig.readconfig(self.path_config)
        if not self.envconfig.recreate and rconfig and \
            rconfig.matches(self._getliveconfig()):
            action.info("reusing", self.envconfig.envdir)
            return
        if rconfig is None:
            action.setactivity("create", self.envconfig.envdir)
        else:
            action.setactivity("recreate", self.envconfig.envdir)
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
            return "could not install deps %s; v = %r" % (
                self.envconfig.deps, v)

    def _getliveconfig(self):
        python = self.envconfig._basepython_info.executable
        md5 = getdigest(python)
        version = tox.__version__
        distribute = self.envconfig.distribute
        sitepackages = self.envconfig.sitepackages
        develop = self.envconfig.develop
        deps = []
        for dep in self._getresolvedeps():
            raw_dep = dep.name
            md5 = getdigest(raw_dep)
            deps.append((md5, raw_dep))
        return CreationConfig(md5, python, version,
                        distribute, sitepackages, develop, deps)

    def _getresolvedeps(self):
        l = []
        for dep in self.envconfig.deps:
            if dep.indexserver is None:
                res = self.session._resolve_pkg(dep.name)
                if res != dep.name:
                    dep = dep.__class__(res)
            l.append(dep)
        return l

    def getsupportedinterpreter(self):
        return self.envconfig.getsupportedinterpreter()

    def create(self, action=None):
        #if self.getcommandpath("activate").dirpath().check():
        #    return
        if action is None:
            action = self.session.newaction(self, "create")

        config_interpreter = self.getsupportedinterpreter()
        args = [sys.executable, '-mvirtualenv']
        if self.envconfig.distribute:
            args.append("--distribute")
        else:
            args.append("--setuptools")
        if self.envconfig.sitepackages:
            args.append('--system-site-packages')
        # add interpreter explicitly, to prevent using
        # default (virtualenv.ini)
        args.extend(['--python', str(config_interpreter)])
        #if sys.platform == "win32":
        #    f, path, _ = py.std.imp.find_module("virtualenv")
        #    f.close()
        #    args[:1] = [str(config_interpreter), str(path)]
        #else:
        self.session.make_emptydir(self.path)
        basepath = self.path.dirpath()
        basepath.ensure(dir=1)
        args.append(self.path.basename)
        self._pcall(args, venv=False, action=action, cwd=basepath)
        self.just_created = True


    def finish(self):
        self._getliveconfig().writeconfig(self.path_config)

    def _needs_reinstall(self, setupdir, action):
        setup_py = setupdir.join('setup.py')
        setup_cfg = setupdir.join('setup.cfg')
        args = [self.envconfig.envpython, str(setup_py), '--name']
        output = action.popen(args, cwd=setupdir, redirect=False,
                              returnout=True)
        name = output.strip()
        egg_info = setupdir.join('.'.join((name, 'egg-info')))
        for conf_file in (setup_py, setup_cfg):
            if (not egg_info.check() or (conf_file.check()
                    and conf_file.mtime() > egg_info.mtime())):
                return True
        return False

    def developpkg(self, setupdir, action):
        assert action is not None
        if getattr(self, 'just_created', False):
            action.setactivity("develop-inst", setupdir)
            self.finish()
            extraopts = []
        else:
            if not self._needs_reinstall(setupdir, action):
                action.setactivity("develop-inst-noop", setupdir)
                return
            action.setactivity("develop-inst-nodeps", setupdir)
            extraopts = ['--no-deps']
        self._install(['-e', setupdir], extraopts=extraopts, action=action)

    def installpkg(self, sdistpath, action):
        assert action is not None
        if getattr(self, 'just_created', False):
            action.setactivity("inst", sdistpath)
            self.finish()
            extraopts = []
        else:
            action.setactivity("inst-nodeps", sdistpath)
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

    def _installopts(self, indexserver):
        l = []
        if indexserver:
            l += ["-i", indexserver]
        if self.envconfig.downloadcache:
            self.envconfig.downloadcache.ensure(dir=1)
            l.append("--download-cache=%s" % self.envconfig.downloadcache)
        return l

    def run_install_command(self, packages, options=(),
                            indexserver=None, action=None,
                            extraenv=None):
        argv = self.envconfig.install_command[:]
        # use pip-script on win32 to avoid the executable locking
        i = argv.index('{packages}')
        argv[i:i+1] = packages
        if '{opts}' in argv:
            i = argv.index('{opts}')
            argv[i:i+1] = list(options)
        for x in ('PIP_RESPECT_VIRTUALENV', 'PIP_REQUIRE_VIRTUALENV',
                  '__PYVENV_LAUNCHER__'):
            try:
                del os.environ[x]
            except KeyError:
                pass
        old_stdout = sys.stdout
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)
        if extraenv is None:
            extraenv = {}
        self._pcall(argv, cwd=self.envconfig.config.toxinidir,
                    extraenv=extraenv, action=action)
        sys.stdout = old_stdout

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
            d.setdefault(ixserver, []).append(dep.name)
            if ixserver not in l:
                l.append(ixserver)
            assert ixserver.url is None or isinstance(ixserver.url, str)

        for ixserver in l:
            if self.envconfig.config.option.sethome:
                extraenv = hack_home_env(
                    homedir=self.envconfig.envtmpdir.join("pseudo-home"),
                    index_url = ixserver.url)
            else:
                extraenv = {}

            packages = d[ixserver]
            options = self._installopts(ixserver.url)
            if extraopts:
                options.extend(extraopts)
            self.run_install_command(packages=packages, options=options,
                                     action=action, extraenv=extraenv)

    def _getenv(self, extraenv={}):
        env = os.environ.copy()
        setenv = self.envconfig.setenv
        if setenv:
            env.update(setenv)
        env['VIRTUAL_ENV'] = str(self.path)
        env.update(extraenv)
        return env

    def test(self, redirect=False):
        action = self.session.newaction(self, "runtests")
        with action:
            self.status = 0
            self.session.make_emptydir(self.envconfig.envtmpdir)
            cwd = self.envconfig.changedir
            env = self._getenv()
            # Display PYTHONHASHSEED to assist with reproducibility.
            action.setactivity("runtests", "PYTHONHASHSEED=%r" % env.get('PYTHONHASHSEED'))
            for i, argv in enumerate(self.envconfig.commands):
                # have to make strings as _pcall changes argv[0] to a local()
                # happens if the same environment is invoked twice
                message = "commands[%s] | %s" % (i, ' '.join(
                    [str(x) for x in argv]))
                action.setactivity("runtests", message)
                try:
                    self._pcall(argv, cwd=cwd, action=action, redirect=redirect)
                except tox.exception.InvocationError:
                    val = sys.exc_info()[1]
                    self.session.report.error(str(val))
                    self.status = "commands failed"
                except KeyboardInterrupt:
                    self.status = "keyboardinterrupt"
                    self.session.report.error(self.status)
                    raise

    def _pcall(self, args, venv=True, cwd=None, extraenv={},
            action=None, redirect=True):
        for name in ("VIRTUALENV_PYTHON", "PYTHONDONTWRITEBYTECODE"):
            try:
                del os.environ[name]
            except KeyError:
                pass
        assert cwd
        cwd.ensure(dir=1)
        old = self.patchPATH()
        try:
            args[0] = self.getcommandpath(args[0], venv, cwd)
            env = self._getenv(extraenv)
            return action.popen(args, cwd=cwd, env=env, redirect=redirect)
        finally:
            os.environ['PATH'] = old

    def patchPATH(self):
        oldPATH = os.environ['PATH']
        bindir = str(self.envconfig.envbindir)
        os.environ['PATH'] = os.pathsep.join([bindir, oldPATH])
        self.session.report.verbosity2("setting PATH=%s" % os.environ["PATH"])
        return oldPATH


def getdigest(path):
    path = py.path.local(path)
    if not path.check(file=1):
        return "0" * 32
    return path.computehash()


def hack_home_env(homedir, index_url=None):
    # XXX HACK (this could also live with tox itself, consider)
    # if tox uses pip on a package that requires setup_requires
    # the index url set with pip is usually not recognized
    # because it is setuptools executing very early.
    # We therefore run the tox command in an artifical home
    # directory and set .pydistutils.cfg and pip.conf files
    # accordingly.
    if not homedir.check():
        homedir.ensure(dir=1)
    d = dict(HOME=str(homedir))
    if not index_url:
        index_url = os.environ.get("TOX_INDEX_URL")
    if index_url:
        homedir.join(".pydistutils.cfg").write(
            "[easy_install]\n"
            "index_url = %s\n" % index_url)
        d["PIP_INDEX_URL"] = index_url
        d["TOX_INDEX_URL"] = index_url
    return d
