import ast
import codecs
import os
import pipes
import re
import sys
import warnings

import py

import tox

from .config import DepConfig


class CreationConfig:
    def __init__(self, md5, python, version, sitepackages, usedevelop, deps, alwayscopy):
        self.md5 = md5
        self.python = python
        self.version = version
        self.sitepackages = sitepackages
        self.usedevelop = usedevelop
        self.alwayscopy = alwayscopy
        self.deps = deps

    def writeconfig(self, path):
        lines = [
            "{} {}".format(self.md5, self.python),
            "{} {:d} {:d} {:d}".format(
                self.version, self.sitepackages, self.usedevelop, self.alwayscopy
            ),
        ]
        for dep in self.deps:
            lines.append("{} {}".format(*dep))
        path.ensure()
        path.write("\n".join(lines))

    @classmethod
    def readconfig(cls, path):
        try:
            lines = path.readlines(cr=0)
            value = lines.pop(0).split(None, 1)
            md5, python = value
            version, sitepackages, usedevelop, alwayscopy = lines.pop(0).split(None, 4)
            sitepackages = bool(int(sitepackages))
            usedevelop = bool(int(usedevelop))
            alwayscopy = bool(int(alwayscopy))
            deps = []
            for line in lines:
                md5, depstring = line.split(None, 1)
                deps.append((md5, depstring))
            return CreationConfig(md5, python, version, sitepackages, usedevelop, deps, alwayscopy)
        except Exception:
            return None

    def matches(self, other):
        return (
            other
            and self.md5 == other.md5
            and self.python == other.python
            and self.version == other.version
            and self.sitepackages == other.sitepackages
            and self.usedevelop == other.usedevelop
            and self.alwayscopy == other.alwayscopy
            and self.deps == other.deps
        )


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
        return "<VirtualEnv at {!r}>".format(self.path)

    def getcommandpath(self, name, venv=True, cwd=None):
        """ Return absolute path (str or localpath) for specified command name.

        - If it's a local path we will rewrite it as as a relative path.
        - If venv is True we will check if the command is coming from the venv
          or is whitelisted to come from external.
        """
        name = str(name)
        if os.path.isabs(name):
            return name
        if os.path.split(name)[0] == ".":
            path = cwd.join(name)
            if path.check():
                return str(path)

        if venv:
            path = self._venv_lookup_and_check_external_whitelist(name)
        else:
            path = self._normal_lookup(name)

        if path is None:
            raise tox.exception.InvocationError("could not find executable {!r}".format(name))

        return str(path)  # will not be rewritten for reporting

    def _venv_lookup_and_check_external_whitelist(self, name):
        path = self._venv_lookup(name)
        if path is None:
            path = self._normal_lookup(name)
            if path is not None:
                self._check_external_allowed_and_warn(path)
        return path

    def _venv_lookup(self, name):
        return py.path.local.sysfind(name, paths=[self.envconfig.envbindir])

    def _normal_lookup(self, name):
        return py.path.local.sysfind(name)

    def _check_external_allowed_and_warn(self, path):
        if not self.is_allowed_external(path):
            self.session.report.warning(
                "test command found but not installed in testenv\n"
                "  cmd: {}\n"
                "  env: {}\n"
                "Maybe you forgot to specify a dependency? "
                "See also the whitelist_externals envconfig setting.".format(
                    path, self.envconfig.envdir
                )
            )

    def is_allowed_external(self, p):
        tryadd = [""]
        if tox.INFO.IS_WIN:
            tryadd += [os.path.normcase(x) for x in os.environ["PATHEXT"].split(os.pathsep)]
            p = py.path.local(os.path.normcase(str(p)))
        for x in self.envconfig.whitelist_externals:
            for add in tryadd:
                if p.fnmatch(x + add):
                    return True
        return False

    def update(self, action):
        """ return status string for updating actual venv to match configuration.
            if status string is empty, all is ok.
        """
        rconfig = CreationConfig.readconfig(self.path_config)
        if not self.envconfig.recreate and rconfig and rconfig.matches(self._getliveconfig()):
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
        try:
            self.hook.tox_testenv_install_deps(action=action, venv=self)
        except tox.exception.InvocationError:
            v = sys.exc_info()[1]
            return "could not install deps {}; v = {!r}".format(self.envconfig.deps, v)

    def _getliveconfig(self):
        python = self.envconfig.python_info.executable
        md5 = getdigest(python)
        version = tox.__version__
        sitepackages = self.envconfig.sitepackages
        develop = self.envconfig.usedevelop
        alwayscopy = self.envconfig.alwayscopy
        deps = []
        for dep in self.get_resolved_dependencies():
            raw_dep = dep.name
            md5 = getdigest(raw_dep)
            deps.append((md5, raw_dep))
        return CreationConfig(md5, python, version, sitepackages, develop, deps, alwayscopy)

    def _getresolvedeps(self):
        warnings.warn(
            "that's a private function there, use get_resolved_dependencies,"
            "this will be removed in 3.2",
            category=DeprecationWarning,
        )
        return self.get_resolved_dependencies()

    def get_resolved_dependencies(self):
        dependencies = []
        for dependency in self.envconfig.deps:
            if dependency.indexserver is None:
                package = self.session._resolve_package(package_spec=dependency.name)
                if package != dependency.name:
                    dependency = dependency.__class__(package)
            dependencies.append(dependency)
        return dependencies

    def getsupportedinterpreter(self):
        return self.envconfig.getsupportedinterpreter()

    def matching_platform(self):
        return re.match(self.envconfig.platform, sys.platform)

    def finish(self):
        self._getliveconfig().writeconfig(self.path_config)

    def _needs_reinstall(self, setupdir, action):
        setup_py = setupdir.join("setup.py")
        setup_cfg = setupdir.join("setup.cfg")
        args = [self.envconfig.envpython, str(setup_py), "--name"]
        env = self._getenv()
        output = action.popen(args, cwd=setupdir, redirect=False, returnout=True, env=env)
        name = output.strip()
        args = [self.envconfig.envpython, "-c", "import sys; print(sys.path)"]
        out = action.popen(args, redirect=False, returnout=True, env=env)
        try:
            sys_path = ast.literal_eval(out.strip())
        except SyntaxError:
            sys_path = []
        egg_info_fname = ".".join((name, "egg-info"))
        for d in reversed(sys_path):
            egg_info = py.path.local(d).join(egg_info_fname)
            if egg_info.check():
                break
        else:
            return True
        return any(
            conf_file.check() and conf_file.mtime() > egg_info.mtime()
            for conf_file in (setup_py, setup_cfg)
        )

    def developpkg(self, setupdir, action):
        assert action is not None
        if getattr(self, "just_created", False):
            action.setactivity("develop-inst", setupdir)
            self.finish()
            extraopts = []
        else:
            if not self._needs_reinstall(setupdir, action):
                action.setactivity("develop-inst-noop", setupdir)
                return
            action.setactivity("develop-inst-nodeps", setupdir)
            extraopts = ["--no-deps"]

        if action.venv.envconfig.extras:
            setupdir += "[{}]".format(",".join(action.venv.envconfig.extras))

        self._install(["-e", setupdir], extraopts=extraopts, action=action)

    def installpkg(self, sdistpath, action):
        assert action is not None
        if getattr(self, "just_created", False):
            action.setactivity("inst", sdistpath)
            self.finish()
            extraopts = []
        else:
            action.setactivity("inst-nodeps", sdistpath)
            extraopts = ["-U", "--no-deps"]

        if action.venv.envconfig.extras:
            sdistpath += "[{}]".format(",".join(action.venv.envconfig.extras))

        self._install([sdistpath], extraopts=extraopts, action=action)

    def _installopts(self, indexserver):
        options = []
        if indexserver:
            options += ["-i", indexserver]
        if self.envconfig.pip_pre:
            options.append("--pre")
        return options

    def run_install_command(self, packages, action, options=()):
        argv = self.envconfig.install_command[:]
        i = argv.index("{packages}")
        argv[i : i + 1] = packages
        if "{opts}" in argv:
            i = argv.index("{opts}")
            argv[i : i + 1] = list(options)

        for x in ("PIP_RESPECT_VIRTUALENV", "PIP_REQUIRE_VIRTUALENV", "__PYVENV_LAUNCHER__"):
            os.environ.pop(x, None)

        if "PYTHONPATH" not in self.envconfig.passenv:
            # If PYTHONPATH not explicitly asked for, remove it.
            if "PYTHONPATH" in os.environ:
                self.session.report.warning(
                    "Discarding $PYTHONPATH from environment, to override "
                    "specify PYTHONPATH in 'passenv' in your configuration."
                )
                os.environ.pop("PYTHONPATH")

        old_stdout = sys.stdout
        sys.stdout = codecs.getwriter("utf8")(sys.stdout)
        try:
            self._pcall(
                argv,
                cwd=self.envconfig.config.toxinidir,
                action=action,
                redirect=self.session.report.verbosity < 2,
            )
        finally:
            sys.stdout = old_stdout

    def _install(self, deps, extraopts=None, action=None):
        if not deps:
            return
        d = {}
        ixservers = []
        for dep in deps:
            if isinstance(dep, (str, py.path.local)):
                dep = DepConfig(str(dep), None)
            assert isinstance(dep, DepConfig), dep
            if dep.indexserver is None:
                ixserver = self.envconfig.config.indexserver["default"]
            else:
                ixserver = dep.indexserver
            d.setdefault(ixserver, []).append(dep.name)
            if ixserver not in ixservers:
                ixservers.append(ixserver)
            assert ixserver.url is None or isinstance(ixserver.url, str)

        for ixserver in ixservers:
            packages = d[ixserver]
            options = self._installopts(ixserver.url)
            if extraopts:
                options.extend(extraopts)
            self.run_install_command(packages=packages, options=options, action=action)

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

        env["VIRTUAL_ENV"] = str(self.path)
        return env

    def test(self, redirect=False):
        with self.session.newaction(self, "runtests") as action:
            self.status = 0
            self.session.make_emptydir(self.envconfig.envtmpdir)
            self.envconfig.envtmpdir.ensure(dir=1)
            cwd = self.envconfig.changedir
            env = self._getenv(testcommand=True)
            # Display PYTHONHASHSEED to assist with reproducibility.
            action.setactivity("runtests", "PYTHONHASHSEED={!r}".format(env.get("PYTHONHASHSEED")))
            for i, argv in enumerate(self.envconfig.commands):
                # have to make strings as _pcall changes argv[0] to a local()
                # happens if the same environment is invoked twice
                message = "commands[{}] | {}".format(
                    i, " ".join([pipes.quote(str(x)) for x in argv])
                )
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
                    self._pcall(
                        argv,
                        cwd=cwd,
                        action=action,
                        redirect=redirect,
                        ignore_ret=ignore_ret,
                        testcommand=True,
                    )
                except tox.exception.InvocationError as err:
                    if self.envconfig.ignore_outcome:
                        msg = "command failed but result from testenv is ignored\ncmd:"
                        self.session.report.warning("{} {}".format(msg, err))
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

    def _pcall(
        self, args, cwd, venv=True, testcommand=False, action=None, redirect=True, ignore_ret=False
    ):
        os.environ.pop("VIRTUALENV_PYTHON", None)

        cwd.ensure(dir=1)
        args[0] = self.getcommandpath(args[0], venv, cwd)
        if sys.platform != "win32" and "TOX_LIMITED_SHEBANG" in os.environ:
            args = prepend_shebang_interpreter(args)
        env = self._getenv(testcommand=testcommand)
        bindir = str(self.envconfig.envbindir)
        env["PATH"] = p = os.pathsep.join([bindir, os.environ["PATH"]])
        self.session.report.verbosity2("setting PATH={}".format(p))
        return action.popen(args, cwd=cwd, env=env, redirect=redirect, ignore_ret=ignore_ret)


def getdigest(path):
    path = py.path.local(path)
    if not path.check(file=1):
        return "0" * 32
    return path.computehash()


def prepend_shebang_interpreter(args):
    # prepend interpreter directive (if any) to argument list
    #
    # When preparing virtual environments in a file container which has large
    # length, the system might not be able to invoke shebang scripts which
    # define interpreters beyond system limits (e.x. Linux as a limit of 128;
    # BINPRM_BUF_SIZE). This method can be used to check if the executable is
    # a script containing a shebang line. If so, extract the interpreter (and
    # possible optional argument) and prepend the values to the provided
    # argument list. tox will only attempt to read an interpreter directive of
    # a maximum size of 2048 bytes to limit excessive reading and support UNIX
    # systems which may support a longer interpret length.
    try:
        with open(args[0], "rb") as f:
            if f.read(1) == b"#" and f.read(1) == b"!":
                MAXINTERP = 2048
                interp = f.readline(MAXINTERP).rstrip()
                interp_args = interp.split(None, 1)[:2]
                return interp_args + args
    except IOError:
        pass
    return args


@tox.hookimpl
def tox_testenv_create(venv, action):
    config_interpreter = venv.getsupportedinterpreter()
    args = [sys.executable, "-m", "virtualenv"]
    if venv.envconfig.sitepackages:
        args.append("--system-site-packages")
    if venv.envconfig.alwayscopy:
        args.append("--always-copy")
    # add interpreter explicitly, to prevent using default (virtualenv.ini)
    args.extend(["--python", str(config_interpreter)])
    venv.session.make_emptydir(venv.path)
    basepath = venv.path.dirpath()
    basepath.ensure(dir=1)
    args.append(venv.path.basename)
    venv._pcall(args, venv=False, action=action, cwd=basepath)
    return True  # Return non-None to indicate plugin has completed


@tox.hookimpl
def tox_testenv_install_deps(venv, action):
    deps = venv.get_resolved_dependencies()
    if deps:
        depinfo = ", ".join(map(str, deps))
        action.setactivity("installdeps", depinfo)
        venv._install(deps, action=action)
    return True  # Return non-None to indicate plugin has completed


@tox.hookimpl
def tox_runtest(venv, redirect):
    venv.test(redirect=redirect)
    return True  # Return non-None to indicate plugin has completed


@tox.hookimpl
def tox_runenvreport(venv, action):
    # write out version dependency information
    args = venv.envconfig.list_dependencies_command
    output = venv._pcall(args, cwd=venv.envconfig.config.toxinidir, action=action)
    # the output contains a mime-header, skip it
    output = output.split("\n\n")[-1]
    packages = output.strip().split("\n")
    return packages  # Return non-None to indicate plugin has completed
