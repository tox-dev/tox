"""
Automatically package and test a Python project against configurable
Python2 and Python3 based virtual environments. Environments are
setup by using virtualenv. Configuration is generally done through an
INI-style "tox.ini" file.
"""
from __future__ import print_function

import os
import re
import shutil
import subprocess
import sys
import time

import py

import tox
from tox._verlib import IrrationalVersionError
from tox._verlib import NormalizedVersion
from tox.config import parseconfig
from tox.result import ResultLog
from tox.venv import VirtualEnv


def prepare(args):
    config = parseconfig(args)
    if config.option.help:
        show_help(config)
        raise SystemExit(0)
    elif config.option.helpini:
        show_help_ini(config)
        raise SystemExit(0)
    return config


def main(args=None):
    try:
        config = prepare(args)
        retcode = Session(config).runcommand()
        raise SystemExit(retcode)
    except KeyboardInterrupt:
        raise SystemExit(2)
    except tox.exception.MinVersionError as e:
        r = Reporter(None)
        r.error(str(e))
        raise SystemExit(1)


def show_help(config):
    tw = py.io.TerminalWriter()
    tw.write(config._parser._format_help())
    tw.line()
    tw.line("Environment variables", bold=True)
    tw.line("TOXENV: comma separated list of environments "
            "(overridable by '-e')")
    tw.line("TOX_TESTENV_PASSENV: space-separated list of extra "
            "environment variables to be passed into test command "
            "environments")


def show_help_ini(config):
    tw = py.io.TerminalWriter()
    tw.sep("-", "per-testenv attributes")
    for env_attr in config._testenv_attr:
        tw.line("%-15s %-8s default: %s" %
                (env_attr.name, "<" + env_attr.type + ">", env_attr.default), bold=True)
        tw.line(env_attr.help)
        tw.line()


class Action(object):
    def __init__(self, session, venv, msg, args):
        self.venv = venv
        self.msg = msg
        self.activity = msg.split(" ", 1)[0]
        self.session = session
        self.report = session.report
        self.args = args
        self.id = venv and venv.envconfig.envname or "tox"
        self._popenlist = []
        if self.venv:
            self.venvname = self.venv.name
        else:
            self.venvname = "GLOB"
        if msg == "runtests":
            cat = "test"
        else:
            cat = "setup"
        envlog = session.resultlog.get_envlog(self.venvname)
        self.commandlog = envlog.get_commandlog(cat)

    def __enter__(self):
        self.report.logaction_start(self)

    def __exit__(self, *args):
        self.report.logaction_finish(self)

    def setactivity(self, name, msg):
        self.activity = name
        self.report.verbosity0("%s %s: %s" % (self.venvname, name, msg), bold=True)

    def info(self, name, msg):
        self.report.verbosity1("%s %s: %s" % (self.venvname, name, msg), bold=True)

    def _initlogpath(self, actionid):
        if self.venv:
            logdir = self.venv.envconfig.envlogdir
        else:
            logdir = self.session.config.logdir
        try:
            l = logdir.listdir("%s-*" % actionid)
        except (py.error.ENOENT, py.error.ENOTDIR):
            logdir.ensure(dir=1)
            l = []
        num = len(l)
        path = logdir.join("%s-%s.log" % (actionid, num))
        f = path.open('w')
        f.flush()
        return f

    def popen(self, args, cwd=None, env=None, redirect=True, returnout=False, ignore_ret=False):
        stdout = outpath = None
        resultjson = self.session.config.option.resultjson
        if resultjson or redirect:
            fout = self._initlogpath(self.id)
            fout.write("actionid: %s\nmsg: %s\ncmdargs: %r\n\n" % (self.id, self.msg, args))
            fout.flush()
            self.popen_outpath = outpath = py.path.local(fout.name)
            fin = outpath.open()
            fin.read()  # read the header, so it won't be written to stdout
            stdout = fout
        elif returnout:
            stdout = subprocess.PIPE
        if cwd is None:
            # XXX cwd = self.session.config.cwd
            cwd = py.path.local()
        try:
            popen = self._popen(args, cwd, env=env,
                                stdout=stdout, stderr=subprocess.STDOUT)
        except OSError as e:
            self.report.error("invocation failed (errno %d), args: %s, cwd: %s" %
                              (e.errno, args, cwd))
            raise
        popen.outpath = outpath
        popen.args = [str(x) for x in args]
        popen.cwd = cwd
        popen.action = self
        self._popenlist.append(popen)
        try:
            self.report.logpopen(popen, env=env)
            try:
                if resultjson and not redirect:
                    assert popen.stderr is None  # prevent deadlock
                    out = None
                    last_time = time.time()
                    while 1:
                        fin_pos = fin.tell()
                        # we have to read one byte at a time, otherwise there
                        # might be no output for a long time with slow tests
                        data = fin.read(1)
                        if data:
                            sys.stdout.write(data)
                            if '\n' in data or (time.time() - last_time) > 1:
                                # we flush on newlines or after 1 second to
                                # provide quick enough feedback to the user
                                # when printing a dot per test
                                sys.stdout.flush()
                                last_time = time.time()
                        elif popen.poll() is not None:
                            if popen.stdout is not None:
                                popen.stdout.close()
                            break
                        else:
                            time.sleep(0.1)
                            fin.seek(fin_pos)
                    fin.close()
                else:
                    out, err = popen.communicate()
            except KeyboardInterrupt:
                self.report.keyboard_interrupt()
                popen.wait()
                raise KeyboardInterrupt()
            ret = popen.wait()
        finally:
            self._popenlist.remove(popen)
        if ret and not ignore_ret:
            invoked = " ".join(map(str, popen.args))
            if outpath:
                self.report.error("invocation failed (exit code %d), logfile: %s" %
                                  (ret, outpath))
                out = outpath.read()
                self.report.error(out)
                if hasattr(self, "commandlog"):
                    self.commandlog.add_command(popen.args, out, ret)
                raise tox.exception.InvocationError(
                    "%s (see %s)" % (invoked, outpath), ret)
            else:
                raise tox.exception.InvocationError("%r" % (invoked, ), ret)
        if not out and outpath:
            out = outpath.read()
        if hasattr(self, "commandlog"):
            self.commandlog.add_command(popen.args, out, ret)
        return out

    def _rewriteargs(self, cwd, args):
        newargs = []
        for arg in args:
            if sys.platform != "win32" and isinstance(arg, py.path.local):
                arg = cwd.bestrelpath(arg)
            newargs.append(str(arg))

        # subprocess does not always take kindly to .py scripts
        # so adding the interpreter here.
        if sys.platform == "win32":
            ext = os.path.splitext(str(newargs[0]))[1].lower()
            if ext == '.py' and self.venv:
                newargs = [str(self.venv.envconfig.envpython)] + newargs

        return newargs

    def _popen(self, args, cwd, stdout, stderr, env=None):
        args = self._rewriteargs(cwd, args)
        if env is None:
            env = os.environ.copy()
        return self.session.popen(args, shell=False, cwd=str(cwd),
                                  universal_newlines=True,
                                  stdout=stdout, stderr=stderr, env=env)


class Reporter(object):
    actionchar = "-"

    def __init__(self, session):
        self.tw = py.io.TerminalWriter()
        self.session = session
        self._reportedlines = []
        # self.cumulated_time = 0.0

    @property
    def verbosity(self):
        if self.session:
            return self.session.config.option.verbosity
        else:
            return 2

    def logpopen(self, popen, env):
        """ log information about the action.popen() created process. """
        cmd = " ".join(map(str, popen.args))
        if popen.outpath:
            self.verbosity1("  %s$ %s >%s" % (popen.cwd, cmd, popen.outpath,))
        else:
            self.verbosity1("  %s$ %s " % (popen.cwd, cmd))

    def logaction_start(self, action):
        msg = action.msg + " " + " ".join(map(str, action.args))
        self.verbosity2("%s start: %s" % (action.venvname, msg), bold=True)
        assert not hasattr(action, "_starttime")
        action._starttime = time.time()

    def logaction_finish(self, action):
        duration = time.time() - action._starttime
        # self.cumulated_time += duration
        self.verbosity2("%s finish: %s after %.2f seconds" % (
            action.venvname, action.msg, duration), bold=True)
        delattr(action, '_starttime')

    def startsummary(self):
        self.tw.sep("_", "summary")

    def info(self, msg):
        if self.verbosity >= 2:
            self.logline(msg)

    def using(self, msg):
        if self.verbosity >= 1:
            self.logline("using %s" % (msg,), bold=True)

    def keyboard_interrupt(self):
        self.error("KEYBOARDINTERRUPT")

#    def venv_installproject(self, venv, pkg):
#        self.logline("installing to %s: %s" % (venv.envconfig.envname, pkg))

    def keyvalue(self, name, value):
        if name.endswith(":"):
            name += " "
        self.tw.write(name, bold=True)
        self.tw.write(value)
        self.tw.line()

    def line(self, msg, **opts):
        self.logline(msg, **opts)

    def good(self, msg):
        self.logline(msg, green=True)

    def warning(self, msg):
        self.logline("WARNING:" + msg, red=True)

    def error(self, msg):
        self.logline("ERROR: " + msg, red=True)

    def skip(self, msg):
        self.logline("SKIPPED:" + msg, yellow=True)

    def logline(self, msg, **opts):
        self._reportedlines.append(msg)
        self.tw.line("%s" % msg, **opts)

    def verbosity0(self, msg, **opts):
        if self.verbosity >= 0:
            self.logline("%s" % msg, **opts)

    def verbosity1(self, msg, **opts):
        if self.verbosity >= 1:
            self.logline("%s" % msg, **opts)

    def verbosity2(self, msg, **opts):
        if self.verbosity >= 2:
            self.logline("%s" % msg, **opts)

    # def log(self, msg):
    #    print(msg, file=sys.stderr)


class Session:
    """ (unstable API).  the session object that ties
    together configuration, reporting, venv creation, testing. """

    def __init__(self, config, popen=subprocess.Popen, Report=Reporter):
        self.config = config
        self.popen = popen
        self.resultlog = ResultLog()
        self.report = Report(self)
        self.make_emptydir(config.logdir)
        config.logdir.ensure(dir=1)
        # self.report.using("logdir %s" %(self.config.logdir,))
        self.report.using("tox.ini: %s" % (self.config.toxinipath,))
        self._spec2pkg = {}
        self._name2venv = {}
        try:
            self.venvlist = [
                self.getvenv(x)
                for x in self.config.envlist
            ]
        except LookupError:
            raise SystemExit(1)
        except tox.exception.ConfigError as e:
            self.report.error(str(e))
            raise SystemExit(1)
        self._actions = []

    @property
    def hook(self):
        return self.config.pluginmanager.hook

    def _makevenv(self, name):
        envconfig = self.config.envconfigs.get(name, None)
        if envconfig is None:
            self.report.error("unknown environment %r" % name)
            raise LookupError(name)
        elif envconfig.envdir == self.config.toxinidir:
            self.report.error(
                "venv %r in %s would delete project" % (name, envconfig.envdir))
            raise tox.exception.ConfigError('envdir must not equal toxinidir')
        venv = VirtualEnv(envconfig=envconfig, session=self)
        self._name2venv[name] = venv
        return venv

    def getvenv(self, name):
        """ return a VirtualEnv controler object for the 'name' env.  """
        try:
            return self._name2venv[name]
        except KeyError:
            return self._makevenv(name)

    def newaction(self, venv, msg, *args):
        action = Action(self, venv, msg, args)
        self._actions.append(action)
        return action

    def runcommand(self):
        self.report.using("tox-%s from %s" % (tox.__version__, tox.__file__))
        if self.config.option.showconfig:
            self.showconfig()
        elif self.config.option.listenvs:
            self.showenvs(all_envs=False, description=self.config.option.verbosity > 0)
        elif self.config.option.listenvs_all:
            self.showenvs(all_envs=True, description=self.config.option.verbosity > 0)
        else:
            return self.subcommand_test()

    def _copyfiles(self, srcdir, pathlist, destdir):
        for relpath in pathlist:
            src = srcdir.join(relpath)
            if not src.check():
                self.report.error("missing source file: %s" % (src,))
                raise SystemExit(1)
            target = destdir.join(relpath)
            target.dirpath().ensure(dir=1)
            src.copy(target)

    def _makesdist(self):
        setup = self.config.setupdir.join("setup.py")
        if not setup.check():
            raise tox.exception.MissingFile(setup)
        action = self.newaction(None, "packaging")
        with action:
            action.setactivity("sdist-make", setup)
            self.make_emptydir(self.config.distdir)
            action.popen([sys.executable, setup, "sdist", "--formats=zip",
                          "--dist-dir", self.config.distdir, ],
                         cwd=self.config.setupdir)
            try:
                return self.config.distdir.listdir()[0]
            except py.error.ENOENT:
                # check if empty or comment only
                data = []
                with open(str(setup)) as fp:
                    for line in fp:
                        if line and line[0] == '#':
                            continue
                        data.append(line)
                if not ''.join(data).strip():
                    self.report.error(
                        'setup.py is empty'
                    )
                    raise SystemExit(1)
                self.report.error(
                    'No dist directory found. Please check setup.py, e.g with:\n'
                    '     python setup.py sdist'
                )
                raise SystemExit(1)

    def make_emptydir(self, path):
        if path.check():
            self.report.info("  removing %s" % path)
            shutil.rmtree(str(path), ignore_errors=True)
            path.ensure(dir=1)

    def setupenv(self, venv):
        if venv.envconfig.missing_subs:
            venv.status = (
                "unresolvable substitution(s): %s. "
                "Environment variables are missing or defined recursively." %
                (','.join(["'%s'" % m for m in venv.envconfig.missing_subs])))
            return
        if not venv.matching_platform():
            venv.status = "platform mismatch"
            return  # we simply omit non-matching platforms
        action = self.newaction(venv, "getenv", venv.envconfig.envdir)
        with action:
            venv.status = 0
            envlog = self.resultlog.get_envlog(venv.name)
            try:
                status = venv.update(action=action)
            except IOError as e:
                if e.args[0] != 2:
                    raise
                status = (
                    "Error creating virtualenv. Note that spaces in paths are "
                    "not supported by virtualenv. Error details: %r" % e)
            except tox.exception.InvocationError as e:
                status = (
                    "Error creating virtualenv. Note that some special "
                    "characters (e.g. ':' and unicode symbols) in paths are "
                    "not supported by virtualenv. Error details: %r" % e)
            if status:
                commandlog = envlog.get_commandlog("setup")
                commandlog.add_command(["setup virtualenv"], str(status), 1)
                venv.status = status
                self.report.error(str(status))
                return False
            commandpath = venv.getcommandpath("python")
            envlog.set_python_info(commandpath)
            return True

    def finishvenv(self, venv):
        action = self.newaction(venv, "finishvenv")
        with action:
            venv.finish()
            return True

    def developpkg(self, venv, setupdir):
        action = self.newaction(venv, "developpkg", setupdir)
        with action:
            try:
                venv.developpkg(setupdir, action)
                return True
            except tox.exception.InvocationError:
                venv.status = sys.exc_info()[1]
                return False

    def installpkg(self, venv, path):
        """Install package in the specified virtual environment.

        :param VenvConfig venv: Destination environment
        :param str path: Path to the distribution package.
        :return: True if package installed otherwise False.
        :rtype: bool
        """
        self.resultlog.set_header(installpkg=py.path.local(path))
        action = self.newaction(venv, "installpkg", path)
        with action:
            try:
                venv.installpkg(path, action)
                return True
            except tox.exception.InvocationError:
                venv.status = sys.exc_info()[1]
                return False

    def get_installpkg_path(self):
        """
        :return: Path to the distribution
        :rtype: py.path.local
        """
        if not self.config.option.sdistonly and (self.config.sdistsrc or
                                                 self.config.option.installpkg):
            path = self.config.option.installpkg
            if not path:
                path = self.config.sdistsrc
            path = self._resolve_pkg(path)
            self.report.info("using package %r, skipping 'sdist' activity " %
                             str(path))
        else:
            try:
                path = self._makesdist()
            except tox.exception.InvocationError:
                v = sys.exc_info()[1]
                self.report.error("FAIL could not package project - v = %r" %
                                  v)
                return
            sdistfile = self.config.distshare.join(path.basename)
            if sdistfile != path:
                self.report.info("copying new sdistfile to %r" %
                                 str(sdistfile))
                try:
                    sdistfile.dirpath().ensure(dir=1)
                except py.error.Error:
                    self.report.warning("could not copy distfile to %s" %
                                        sdistfile.dirpath())
                else:
                    path.copy(sdistfile)
        return path

    def subcommand_test(self):
        if self.config.skipsdist:
            self.report.info("skipping sdist step")
            path = None
        else:
            path = self.get_installpkg_path()
            if not path:
                return 2
        if self.config.option.sdistonly:
            return
        for venv in self.venvlist:
            if self.setupenv(venv):
                if venv.envconfig.skip_install:
                    self.finishvenv(venv)
                else:
                    if venv.envconfig.usedevelop:
                        self.developpkg(venv, self.config.setupdir)
                    elif self.config.skipsdist:
                        self.finishvenv(venv)
                    else:
                        self.installpkg(venv, path)

                # write out version dependency information
                action = self.newaction(venv, "envreport")
                with action:
                    args = venv.envconfig.list_dependencies_command
                    output = venv._pcall(args,
                                         cwd=self.config.toxinidir,
                                         action=action)
                    # the output contains a mime-header, skip it
                    output = output.split("\n\n")[-1]
                    packages = output.strip().split("\n")
                    action.setactivity("installed", ",".join(packages))
                    envlog = self.resultlog.get_envlog(venv.name)
                    envlog.set_installed(packages)

                self.runtestenv(venv)
        retcode = self._summary()
        return retcode

    def runtestenv(self, venv, redirect=False):
        if not self.config.option.notest:
            if venv.status:
                return
            self.hook.tox_runtest_pre(venv=venv)
            self.hook.tox_runtest(venv=venv, redirect=redirect)
            self.hook.tox_runtest_post(venv=venv)
        else:
            venv.status = "skipped tests"

    def _summary(self):
        self.report.startsummary()
        retcode = 0
        for venv in self.venvlist:
            status = venv.status
            if isinstance(status, tox.exception.InterpreterNotFound):
                msg = "  %s: %s" % (venv.envconfig.envname, str(status))
                if self.config.option.skip_missing_interpreters:
                    self.report.skip(msg)
                else:
                    retcode = 1
                    self.report.error(msg)
            elif status == "platform mismatch":
                msg = "  %s: %s" % (venv.envconfig.envname, str(status))
                self.report.skip(msg)
            elif status and status == "ignored failed command":
                msg = "  %s: %s" % (venv.envconfig.envname, str(status))
                self.report.good(msg)
            elif status and status != "skipped tests":
                msg = "  %s: %s" % (venv.envconfig.envname, str(status))
                self.report.error(msg)
                retcode = 1
            else:
                if not status:
                    status = "commands succeeded"
                self.report.good("  %s: %s" % (venv.envconfig.envname, status))
        if not retcode:
            self.report.good("  congratulations :)")

        path = self.config.option.resultjson
        if path:
            path = py.path.local(path)
            path.write(self.resultlog.dumps_json())
            self.report.line("wrote json report at: %s" % path)
        return retcode

    def showconfig(self):
        self.info_versions()
        self.report.keyvalue("config-file:", self.config.option.configfile)
        self.report.keyvalue("toxinipath: ", self.config.toxinipath)
        self.report.keyvalue("toxinidir:  ", self.config.toxinidir)
        self.report.keyvalue("toxworkdir: ", self.config.toxworkdir)
        self.report.keyvalue("setupdir:   ", self.config.setupdir)
        self.report.keyvalue("distshare:  ", self.config.distshare)
        self.report.keyvalue("skipsdist:  ", self.config.skipsdist)
        self.report.tw.line()
        for envconfig in self.config.envconfigs.values():
            self.report.line("[testenv:%s]" % envconfig.envname, bold=True)
            for attr in self.config._parser._testenv_attr:
                self.report.line("  %-15s = %s"
                                 % (attr.name, getattr(envconfig, attr.name)))

    def showenvs(self, all_envs=False, description=False):
        env_conf = self.config.envconfigs  # this contains all environments
        default = self.config.envlist  # this only the defaults
        extra = sorted([e for e in env_conf if e not in default]) if all_envs else []
        if description:
            self.report.line('default environments:')
            max_length = max(len(env) for env in (default + extra))

        def report_env(e):
            if description:
                text = env_conf[e].description or '[no description]'
                msg = '{0} -> {1}'.format(e.ljust(max_length), text).strip()
            else:
                msg = e
            self.report.line(msg)
        for e in default:
            report_env(e)
        if all_envs and extra:
            if description:
                self.report.line('')
                self.report.line('additional environments:')
            for e in extra:
                report_env(e)

    def info_versions(self):
        versions = ['tox-%s' % tox.__version__]
        proc = subprocess.Popen(
            (sys.executable, '-m', 'virtualenv', '--version'),
            stdout=subprocess.PIPE,
        )
        out, _ = proc.communicate()
        versions.append('virtualenv-{0}'.format(out.decode('UTF-8').strip()))
        self.report.keyvalue("tool-versions:", " ".join(versions))

    def _resolve_pkg(self, pkgspec):
        try:
            return self._spec2pkg[pkgspec]
        except KeyError:
            self._spec2pkg[pkgspec] = x = self._resolvepkg(pkgspec)
            return x

    def _resolvepkg(self, pkgspec):
        if not os.path.isabs(str(pkgspec)):
            return pkgspec
        p = py.path.local(pkgspec)
        if p.check():
            return p
        if not p.dirpath().check(dir=1):
            raise tox.exception.MissingDirectory(p.dirpath())
        self.report.info("determining %s" % p)
        candidates = p.dirpath().listdir(p.basename)
        if len(candidates) == 0:
            raise tox.exception.MissingDependency(pkgspec)
        if len(candidates) > 1:
            items = []
            for x in candidates:
                ver = getversion(x.basename)
                if ver is not None:
                    items.append((ver, x))
                else:
                    self.report.warning("could not determine version of: %s" %
                                        str(x))
            items.sort()
            if not items:
                raise tox.exception.MissingDependency(pkgspec)
            return items[-1][1]
        else:
            return candidates[0]


_rex_getversion = re.compile(r"[\w_\-\+\.]+-(.*)\.(zip|tar\.gz)")


def getversion(basename):
    m = _rex_getversion.match(basename)
    if m is None:
        return None
    version = m.group(1)
    try:
        return NormalizedVersion(version)
    except IrrationalVersionError:
        return None
