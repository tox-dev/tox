"""
Automatically package and test a Python project against configurable
Python2 and Python3 based virtual environments. Environments are
setup by using virtualenv. Configuration is generally done through an
INI-style "tox.ini" file.
"""
from __future__ import with_statement

import tox
import py
import os
import sys
import subprocess
from tox._verlib import NormalizedVersion, IrrationalVersionError
from tox._venv import VirtualEnv
from tox._config import parseconfig
from tox.result import ResultLog
from subprocess import STDOUT

def now():
    return py.std.time.time()

def main(args=None):
    try:
        config = parseconfig(args, 'tox')
        retcode = Session(config).runcommand()
        raise SystemExit(retcode)
    except KeyboardInterrupt:
        raise SystemExit(2)

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
        cat = {"runtests": "test", "getenv": "setup"}.get(msg)
        if cat:
            envlog = session.resultlog.get_envlog(self.venvname)
            self.commandlog = envlog.get_commandlog(cat)

    def __enter__(self):
        self.report.logaction_start(self)

    def __exit__(self, *args):
        self.report.logaction_finish(self)

    def setactivity(self, name, msg):
        self.activity = name
        self.report.verbosity0("%s %s: %s" %(self.venvname, name, msg),
            bold=True)

    def info(self, name, msg):
        self.report.verbosity1("%s %s: %s" %(self.venvname, name, msg),
            bold=True)

    def _initlogpath(self, actionid):
        if self.venv:
            logdir = self.venv.envconfig.envlogdir
        else:
            logdir = self.session.config.logdir
        try:
            l = logdir.listdir("%s-*" % actionid)
        except py.error.ENOENT:
            logdir.ensure(dir=1)
            l = []
        num = len(l)
        path = logdir.join("%s-%s.log" % (actionid, num))
        f = path.open('w')
        f.flush()
        return f

    def popen(self, args, cwd=None, env=None, redirect=True, returnout=False):
        f = outpath = None
        resultjson = self.session.config.option.resultjson
        if resultjson or redirect:
            f = self._initlogpath(self.id)
            f.write("actionid=%s\nmsg=%s\ncmdargs=%r\nenv=%s\n" %(
                    self.id, self.msg, args, env))
            f.flush()
            self.popen_outpath = outpath = py.path.local(f.name)
        elif returnout:
            f = subprocess.PIPE
        if cwd is None:
            # XXX cwd = self.session.config.cwd
            cwd = py.path.local()
        try:
            popen = self._popen(args, cwd, env=env,
                                stdout=f, stderr=STDOUT)
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
                out, err = popen.communicate()
            except KeyboardInterrupt:
                self.report.keyboard_interrupt()
                popen.wait()
                raise KeyboardInterrupt()
            ret = popen.wait()
        finally:
            self._popenlist.remove(popen)
        if ret:
            invoked = " ".join(map(str, popen.args))
            if outpath:
                self.report.error("invocation failed (exit code %d), logfile: %s" %
                                  (ret, outpath))
                out = outpath.read()
                self.report.error(out)
                if hasattr(self, "commandlog"):
                    self.commandlog.add_command(popen.args, out, ret)
                raise tox.exception.InvocationError(
                    "%s (see %s)" %(invoked, outpath), ret)
            else:
                raise tox.exception.InvocationError("%r" %(invoked, ))
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

        #subprocess does not always take kindly to .py scripts
        #so adding the interpreter here.
        if sys.platform == "win32":
            ext = os.path.splitext(str(newargs[0]))[1].lower()
            if ext == '.py' and self.venv:
                newargs = [str(self.venv.getcommandpath())] + newargs

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
        #self.cumulated_time = 0.0

    def logpopen(self, popen, env):
        """ log information about the action.popen() created process. """
        cmd = " ".join(map(str, popen.args))
        if popen.outpath:
            self.verbosity1("  %s$ %s >%s" %(popen.cwd, cmd,
                popen.outpath,
                ))
        else:
            self.verbosity1("  %s$ %s " %(popen.cwd, cmd))

    def logaction_start(self, action):
        msg = action.msg + " " + " ".join(map(str, action.args))
        self.verbosity2("%s start: %s" %(action.venvname, msg), bold=True)
        assert not hasattr(action, "_starttime")
        action._starttime = now()

    def logaction_finish(self, action):
        duration = now() - action._starttime
        #self.cumulated_time += duration
        self.verbosity2("%s finish: %s after %.2f seconds" %(
            action.venvname, action.msg, duration), bold=True)

    def startsummary(self):
        self.tw.sep("_", "summary")

    def info(self, msg):
        if self.session.config.option.verbosity >= 2:
            self.logline(msg)

    def using(self, msg):
        if self.session.config.option.verbosity >= 1:
            self.logline("using %s" %(msg,), bold=True)


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
        if self.session.config.option.verbosity >= 0:
            self.logline("%s" % msg, **opts)

    def verbosity1(self, msg, **opts):
        if self.session.config.option.verbosity >= 1:
            self.logline("%s" % msg, **opts)

    def verbosity2(self, msg, **opts):
        if self.session.config.option.verbosity >= 2:
            self.logline("%s" % msg, **opts)

    #def log(self, msg):
    #    py.builtin.print_(msg, file=sys.stderr)


class Session:

    def __init__(self, config, popen=subprocess.Popen, Report=Reporter):
        self.config = config
        self.popen = popen
        self.resultlog = ResultLog()
        self.report = Report(self)
        self.make_emptydir(config.logdir)
        config.logdir.ensure(dir=1)
        #self.report.using("logdir %s" %(self.config.logdir,))
        self.report.using("tox.ini: %s" %(self.config.toxinipath,))
        self._spec2pkg = {}
        self._name2venv = {}
        try:
            self.venvlist = [self.getvenv(x)
                for x in self.config.envlist]
        except LookupError:
            raise SystemExit(1)
        self._actions = []

    def _makevenv(self, name):
        envconfig = self.config.envconfigs.get(name, None)
        if envconfig is None:
            self.report.error("unknown environment %r" % name)
            raise LookupError(name)
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
        self.report.using("tox-%s from %s" %(tox.__version__,
                                             tox.__file__))
        if self.config.minversion:
            minversion = NormalizedVersion(self.config.minversion)
            toxversion = NormalizedVersion(tox.__version__)
            if toxversion < minversion:
                self.report.error(
                    "tox version is %s, required is at least %s" %(
                       toxversion, minversion))
                raise SystemExit(1)
        if self.config.option.showconfig:
            self.showconfig()
        elif self.config.option.listenvs:
            self.showenvs()
        else:
            return self.subcommand_test()

    def _copyfiles(self, srcdir, pathlist, destdir):
        for relpath in pathlist:
            src = srcdir.join(relpath)
            if not src.check():
                self.report.error("missing source file: %s" %(src,))
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
                    'No dist directory found. Please check setup.py, e.g with:\n'\
                    '     python setup.py sdist'
                    )
                raise SystemExit(1)


    def make_emptydir(self, path):
        if path.check():
            self.report.info("  removing %s" % path)
            py.std.shutil.rmtree(str(path), ignore_errors=True)
            path.ensure(dir=1)

    def setupenv(self, venv):
        action = self.newaction(venv, "getenv", venv.envconfig.envdir)
        with action:
            venv.status = 0
            envlog = self.resultlog.get_envlog(venv.name)
            try:
                status = venv.update(action=action)
            except tox.exception.InvocationError:
                status = sys.exc_info()[1]
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

    def installpkg(self, venv, sdist_path):
        self.resultlog.set_header(installpkg=sdist_path)
        action = self.newaction(venv, "installpkg", sdist_path)
        with action:
            try:
                venv.installpkg(sdist_path, action)
                return True
            except tox.exception.InvocationError:
                venv.status = sys.exc_info()[1]
                return False

    def sdist(self):
        if not self.config.option.sdistonly and (self.config.sdistsrc or
            self.config.option.installpkg):
            sdist_path = self.config.option.installpkg
            if not sdist_path:
                sdist_path = self.config.sdistsrc
            sdist_path = self._resolve_pkg(sdist_path)
            self.report.info("using package %r, skipping 'sdist' activity " %
                str(sdist_path))
        else:
            try:
                sdist_path = self._makesdist()
            except tox.exception.InvocationError:
                v = sys.exc_info()[1]
                self.report.error("FAIL could not package project - v = %r" %
                    v)
                return
            sdistfile = self.config.distshare.join(sdist_path.basename)
            if sdistfile != sdist_path:
                self.report.info("copying new sdistfile to %r" %
                    str(sdistfile))
                try:
                    sdistfile.dirpath().ensure(dir=1)
                except py.error.Error:
                    self.report.warning("could not copy distfile to %s" %
                                        sdistfile.dirpath())
                else:
                    sdist_path.copy(sdistfile)
        return sdist_path

    def subcommand_test(self):
        if self.config.skipsdist:
            self.report.info("skipping sdist step")
            sdist_path = None
        else:
            sdist_path = self.sdist()
            if not sdist_path:
                return 2
        if self.config.option.sdistonly:
            return
        for venv in self.venvlist:
            if self.setupenv(venv):
                if venv.envconfig.develop:
                    self.developpkg(venv, self.config.setupdir)
                elif self.config.skipsdist:
                    self.finishvenv(venv)
                else:
                    self.installpkg(venv, sdist_path)
                self.runtestenv(venv)
        retcode = self._summary()
        return retcode

    def runtestenv(self, venv, redirect=False):
        if not self.config.option.notest:
            if venv.status:
                return
            venv.test(redirect=redirect)
        else:
            venv.status = "skipped tests"

    def _summary(self):
        self.report.startsummary()
        retcode = 0
        for venv in self.venvlist:
            status = venv.status
            if isinstance(status, tox.exception.InterpreterNotFound):
                msg = "  %s: %s" %(venv.envconfig.envname, str(status))
                if self.config.option.skip_missing_interpreters:
                    self.report.skip(msg)
                else:
                    retcode = 1
                    self.report.error(msg)
            elif status and status != "skipped tests":
                msg = "  %s: %s" %(venv.envconfig.envname, str(status))
                self.report.error(msg)
                retcode = 1
            else:
                if not status:
                    status = "commands succeeded"
                self.report.good("  %s: %s" %(venv.envconfig.envname,
                                              status))
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
            self.report.line("  basepython=%s" % envconfig.basepython)
            self.report.line("  _basepython_info=%s" %
                             envconfig._basepython_info)
            self.report.line("  envpython=%s" % envconfig.envpython)
            self.report.line("  envtmpdir=%s" % envconfig.envtmpdir)
            self.report.line("  envbindir=%s" % envconfig.envbindir)
            self.report.line("  envlogdir=%s" % envconfig.envlogdir)
            self.report.line("  changedir=%s" % envconfig.changedir)
            self.report.line("  args_are_path=%s" % envconfig.args_are_paths)
            self.report.line("  install_command=%s" %
                             envconfig.install_command)
            self.report.line("  commands=")
            for command in envconfig.commands:
                self.report.line("    %s" % command)
            self.report.line("  deps=%s" % envconfig.deps)
            self.report.line("  envdir=    %s" % envconfig.envdir)
            self.report.line("  downloadcache=%s" % envconfig.downloadcache)
            self.report.line("  usedevelop=%s" % envconfig.develop)

    def showenvs(self):
        for env in self.config.envlist:
            self.report.line("%s" % env)

    def info_versions(self):
        versions = ['tox-%s' % tox.__version__]
        try:
            version = py.process.cmdexec("virtualenv --version")
        except py.process.cmdexec.Error:
            versions.append("virtualenv-1.9.1 (vendored)")
        else:
            versions.append("virtualenv-%s" % version.strip())
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


_rex_getversion = py.std.re.compile("[\w_\-\+\.]+-(.*)(\.zip|\.tar.gz)")
def getversion(basename):
    m = _rex_getversion.match(basename)
    if m is None:
        return None
    version = m.group(1)
    try:
        return NormalizedVersion(version)
    except IrrationalVersionError:
        return None
