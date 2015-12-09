from __future__ import with_statement
import os
import sys
import re
import codecs
import py
import tox
from .config import DepConfig, hookimpl


class CreationConfig:
    def __init__(self, md5, python, version, sitepackages,
                 usedevelop, deps):
        self.md5 = md5
        self.python = python
        self.version = version
        self.sitepackages = sitepackages
        self.usedevelop = usedevelop
        self.deps = deps

    def writeconfig(self, path):
        lines = ["%s %s" % (self.md5, self.python)]
        lines.append("%s %d %d" % (self.version, self.sitepackages, self.usedevelop))
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
            version, sitepackages, usedevelop = lines.pop(0).split(None, 3)
            sitepackages = bool(int(sitepackages))
            usedevelop = bool(int(usedevelop))
            deps = []
            for line in lines:
                md5, depstring = line.split(None, 1)
                deps.append((md5, depstring))
            return CreationConfig(md5, python, version, sitepackages, usedevelop, deps)
        except Exception:
            return None

    def matches(self, other):
        return (other and self.md5 == other.md5
                and self.python == other.python
                and self.version == other.version
                and self.sitepackages == other.sitepackages
                and self.usedevelop == other.usedevelop
                and self.deps == other.deps)


class VirtualEnv(object):
    def __init__(self, envconfig=None, session=None):
        self.envconfig = envconfig
        self.session = session

    @property
    def hook(self):
        return self.envconfig.config.pluginmanager.hook

    @property
    def path(self):
        """ Path to environment base dir. """
        return self.envconfig.envdir

    @property
    def path_config(self):
        return self.path.join(".tox-config1")

    @property
    def name(self):
        """ test environment name. """
        return self.envconfig.envname

    def __repr__(self):
        return "<VirtualEnv at %r>" % (self.path)

    def getcommandpath(self, name, venv=True, cwd=None):
        """ return absolute path (str or localpath) for specified
        command name.  If it's a localpath we will rewrite it as
        as a relative path.  If venv is True we will check if the
        command is coming from the venv or is whitelisted to come
        from external. """
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
                    "Maybe you forgot to specify a dependency? "
                    "See also the whitelist_externals envconfig setting." % (
                        p, self.envconfig.envdir))
        return str(p)  # will not be rewritten for reporting

    def is_allowed_external(self, p):
        tryadd = [""]
        if sys.platform == "win32":
            tryadd += [
                os.path.normcase(x)
                for x in os.environ['PATHEXT'].split(os.pathsep)
            ]
            p = py.path.local(os.path.normcase(str(p)))
        for x in self.envconfig.whitelist_externals:
            for add in tryadd:
                if p.fnmatch(x + add):
                    return True
        return False

    def _ispython3(self):
        return "python3" in str(self.envconfig.basepython)

    def update(self, action):
        """ return status string for updating actual venv to match configuration.
            if status string is empty, all is ok.
        """
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
            self.hook.tox_testenv_create(action=action, venv=self)
            self.just_created = True
        except tox.exception.UnsupportedInterpreter:
            return sys.exc_info()[1]
        except tox.exception.InterpreterNotFound:
            return sys.exc_info()[1]
        try:
            self.hook.tox_testenv_install_deps(action=action, venv=self)
        except tox.exception.InvocationError:
            v = sys.exc_info()[1]
            return "could not install deps %s; v = %r" % (
                self.envconfig.deps, v)

    def _getliveconfig(self):
        python = self.envconfig.python_info.executable
        md5 = getdigest(python)
        version = tox.__version__
        sitepackages = self.envconfig.sitepackages
        develop = self.envconfig.usedevelop
        deps = []
        for dep in self._getresolvedeps():
            raw_dep = dep.name
            md5 = getdigest(raw_dep)
            deps.append((md5, raw_dep))
        return CreationConfig(md5, python, version,
                              sitepackages, develop, deps)

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

    def matching_platform(self):
        return re.match(self.envconfig.platform, sys.platform)

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
            if (not egg_info.check()
                    or (conf_file.check() and conf_file.mtime() > egg_info.mtime())):
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

    def _installopts(self, indexserver):
        l = []
        if indexserver:
            l += ["-i", indexserver]
        if self.envconfig.downloadcache:
            self.envconfig.downloadcache.ensure(dir=1)
            l.append("--download-cache=%s" % self.envconfig.downloadcache)
        if self.envconfig.pip_pre:
            l.append("--pre")
        return l

    def run_install_command(self, packages, action, options=()):
        argv = self.envconfig.install_command[:]
        # use pip-script on win32 to avoid the executable locking
        i = argv.index('{packages}')
        argv[i:i + 1] = packages
        if '{opts}' in argv:
            i = argv.index('{opts}')
            argv[i:i + 1] = list(options)

        for x in ('PIP_RESPECT_VIRTUALENV', 'PIP_REQUIRE_VIRTUALENV',
                  '__PYVENV_LAUNCHER__'):
            os.environ.pop(x, None)

        old_stdout = sys.stdout
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)
        self._pcall(argv, cwd=self.envconfig.config.toxinidir, action=action)
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
            packages = d[ixserver]
            options = self._installopts(ixserver.url)
            if extraopts:
                options.extend(extraopts)
            self.run_install_command(packages=packages, options=options,
                                     action=action)

    def _getenv(self, testcommand=False):
        if testcommand:
            # for executing tests we construct a clean environment
            env = {}
            for envname in self.envconfig.passenv:
                if envname in os.environ:
                    env[envname] = os.environ[envname]
        else:
            # for executing non-test commands we use the full
            # invocation environment
            env = os.environ.copy()

        # in any case we honor per-testenv setenv configuration
        env.update(self.envconfig.setenv)

        env['VIRTUAL_ENV'] = str(self.path)
        return env

    def test(self, redirect=False):
        action = self.session.newaction(self, "runtests")
        with action:
            self.status = 0
            self.session.make_emptydir(self.envconfig.envtmpdir)
            cwd = self.envconfig.changedir
            env = self._getenv(testcommand=True)
            # Display PYTHONHASHSEED to assist with reproducibility.
            action.setactivity("runtests", "PYTHONHASHSEED=%r" % env.get('PYTHONHASHSEED'))
            for i, argv in enumerate(self.envconfig.commands):
                # have to make strings as _pcall changes argv[0] to a local()
                # happens if the same environment is invoked twice
                message = "commands[%s] | %s" % (i, ' '.join(
                    [str(x) for x in argv]))
                action.setactivity("runtests", message)
                # check to see if we need to ignore the return code
                # if so, we need to alter the command line arguments
                if argv[0].startswith("-"):
                    ignore_ret = True
                    if argv[0] == "-":
                        del argv[0]
                    else:
                        argv[0] = argv[0].lstrip("-")
                else:
                    ignore_ret = False

                try:
                    self._pcall(argv, cwd=cwd, action=action, redirect=redirect,
                                ignore_ret=ignore_ret, testcommand=True)
                except tox.exception.InvocationError as err:
                    if self.envconfig.ignore_outcome:
                        self.session.report.warning(
                            "command failed but result from testenv is ignored\n"
                            "  cmd: %s" % (str(err),))
                        self.status = "ignored failed command"
                        continue  # keep processing commands

                    self.session.report.error(str(err))
                    self.status = "commands failed"
                    if not self.envconfig.ignore_errors:
                        break  # Don't process remaining commands
                except KeyboardInterrupt:
                    self.status = "keyboardinterrupt"
                    self.session.report.error(self.status)
                    raise

    def _pcall(self, args, cwd, venv=True, testcommand=False,
               action=None, redirect=True, ignore_ret=False):
        for name in ("VIRTUALENV_PYTHON", "PYTHONDONTWRITEBYTECODE"):
            os.environ.pop(name, None)

        cwd.ensure(dir=1)
        args[0] = self.getcommandpath(args[0], venv, cwd)
        env = self._getenv(testcommand=testcommand)
        bindir = str(self.envconfig.envbindir)
        env['PATH'] = p = os.pathsep.join([bindir, os.environ["PATH"]])
        self.session.report.verbosity2("setting PATH=%s" % p)
        return action.popen(args, cwd=cwd, env=env,
                            redirect=redirect, ignore_ret=ignore_ret)


def getdigest(path):
    path = py.path.local(path)
    if not path.check(file=1):
        return "0" * 32
    return path.computehash()


@hookimpl
def tox_testenv_create(venv, action):
    # if self.getcommandpath("activate").dirpath().check():
    #    return
    config_interpreter = venv.getsupportedinterpreter()
    args = [sys.executable, '-m', 'virtualenv']
    if venv.envconfig.sitepackages:
        args.append('--system-site-packages')
    # add interpreter explicitly, to prevent using
    # default (virtualenv.ini)
    args.extend(['--python', str(config_interpreter)])
    # if sys.platform == "win32":
    #    f, path, _ = py.std.imp.find_module("virtualenv")
    #    f.close()
    #    args[:1] = [str(config_interpreter), str(path)]
    # else:
    venv.session.make_emptydir(venv.path)
    basepath = venv.path.dirpath()
    basepath.ensure(dir=1)
    args.append(venv.path.basename)
    venv._pcall(args, venv=False, action=action, cwd=basepath)


@hookimpl
def tox_testenv_install_deps(venv, action):
    deps = venv._getresolvedeps()
    if deps:
        depinfo = ", ".join(map(str, deps))
        action.setactivity("installdeps", "%s" % depinfo)
        venv._install(deps, action=action)
