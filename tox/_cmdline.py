"""
Automatically package and test a Python project against configurable
Python2 and Python3 based virtual environments. Environments are
setup by using virtualenv. Configuration is generally done through an
INI-style "tox.ini" file.
"""
import tox
import py
import os
import sys
import subprocess
from tox._verlib import NormalizedVersion, IrrationalVersionError
from tox._venv import VirtualEnv
from tox._config import parseconfig
from subprocess import STDOUT

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

    def setactivity(self, name, msg):
        self.activity = name
        self.report.verbosity0("%s %s: %s" %(self.venvname, name, msg),
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

    def popen(self, args, cwd=None, env=None, redirect=True):
        logged_command = "%s$ %s" %(cwd, " ".join(map(str, args)))
        f = outpath = None
        if redirect:
            f = self._initlogpath(self.id)
            f.write("actionid=%s\nmsg=%s\ncmd=%s\nenv=%s\n" %(
                    self.id, self.msg, logged_command, env))
            f.flush()
            outpath = py.path.local(f.name)
        if cwd is None:
            # XXX cwd = self.session.config.cwd
            cwd = py.path.local()
        popen = self._popen(args, cwd, env=env, stdout=f, stderr=STDOUT)
        popen.outpath = outpath
        popen.args = args
        popen.cwd = cwd
        popen.action = self
        self._popenlist.append(popen)
        self.report.logpopen(popen)
        try:
            out, err = popen.communicate()
        except KeyboardInterrupt:
            self.report.keyboard_interrupt()
            popen.wait()
            raise KeyboardInterrupt()
        ret = popen.wait()
        if ret:
            invoked = " ".join(map(str, popen.args))
            if outpath:
                self.report.error("invocation failed, logfile: %s" % outpath)
                self.report.error(outpath.read())
                raise tox.exception.InvocationError(
                    "%s (see %s)" %(invoked, outpath))
            else:
                raise tox.exception.InvocationError("%r" %(invoked, ))
        return out

    def _rewriteargs(self, cwd, args):
        newargs = []
        for arg in args:
            if isinstance(arg, py.path.local):
                arg = cwd.bestrelpath(arg)
            newargs.append(str(arg))
        return newargs

    def _popen(self, args, cwd, stdout, stderr, env=None):
        args = self._rewriteargs(cwd, args)
        #args = [str(x) for x in args]
        if env is None:
            env = os.environ.copy()
        return self.session.popen(args, stdout=stdout, stderr=stderr,
            cwd=str(cwd), env=env)

class Reporter:
    actionchar = "-"
    def __init__(self, session):
        self.tw = py.io.TerminalWriter()
        self.session = session

    def logpopen(self, popen):
        """ log information about the action.popen() created process. """
        cmd = " ".join(map(str, popen.args))
        if popen.outpath:
            self.verbosity1("  %s$ %s >%s" %(popen.cwd, cmd,
                popen.outpath,
                ))
        else:
            self.verbosity1("  %s$ %s " %(popen.cwd, cmd))

    def logaction(self, action):
        msg = action.msg
        msg += " " + " ".join(map(str, action.args))
        self.logline("%s %s" % (action.venvname, msg,), bold=True)

    def info(self, msg):
        if self.session.config.opts.verbosity >= 2:
            self.logline(msg)

    def using(self, msg):
        if self.session.config.opts.verbosity >= 1:
            self.logline("using %s" %(msg,), bold=True)


    def keyboard_interrupt(self):
        self.tw.line("KEYBOARDINTERRUPT", red=True)

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

    def logline(self, msg, **opts):
        self.tw.line("%s" % msg, **opts)

    def verbosity0(self, msg, **opts):
        if self.session.config.opts.verbosity >= 0:
            self.tw.line("%s" % msg, **opts)

    def verbosity1(self, msg, **opts):
        if self.session.config.opts.verbosity >= 1:
            self.tw.line("%s" % msg, **opts)

    #def log(self, msg):
    #    py.builtin.print_(msg, file=sys.stderr)


class Session:
    passthroughpossible = True

    def __init__(self, config, popen=subprocess.Popen, Report=Reporter):
        self.config = config
        self.popen = popen
        self.report = Report(self)
        self.make_emptydir(config.logdir)
        config.logdir.ensure(dir=1)
        #self.report.using("logdir %s" %(self.config.logdir,))
        self.report.using("tox.ini: %s" %(self.config.toxinipath,))
        self.venvstatus = {}
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
        self.report.logaction(action)
        self._actions.append(action)
        return action

    def runcommand(self):
        #tw.sep("-", "tox info from %s" % self.options.configfile)
        self.report.using("tox-%s from %s" %(tox.__version__, tox.__file__))
        if self.config.minversion:
            minversion = NormalizedVersion(self.config.minversion)
            toxversion = NormalizedVersion(tox.__version__)
            #self.report.using("requires at least %s" %(minversion,))
            if toxversion < minversion:
                self.report.error(
                    "tox version is %s, required is at least %s" %(
                       toxversion, minversion))
                raise SystemExit(1)
        if self.config.opts.showconfig:
            self.showconfig()
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

    def setenvstatus(self, venv, msg):
        self.venvstatus[venv.path] = msg

    def _makesdist(self):
        action = self.newaction(None, "prepare sdist package")
        setup = self.config.setupdir.join("setup.py")
        action.setactivity("sdist-make", "using %s" % setup)
        if not setup.check():
            raise tox.exception.MissingFile(setup)
        self.make_emptydir(self.config.distdir)
        action.popen([sys.executable, setup, "sdist", "--formats=zip",
                      "--dist-dir", self.config.distdir, ],
                      cwd=self.config.setupdir)
        return self.config.distdir.listdir()[0]

    def make_emptydir(self, path):
        if path.check():
            self.report.info("  removing %s" % path)
            py.std.shutil.rmtree(str(path), ignore_errors=True)
            path.ensure(dir=1)

    def setupenv(self, venv, sdist_path):
        action = self.newaction(venv, "prepareenv", venv.envconfig.envdir)
        if self._prepareenv(action, venv):
            if sdist_path is not None:
                self.installsdist(venv, sdist_path)

    def _prepareenv(self, action, venv):
        self.venvstatus[venv.path] = 0
        try:
            status = venv.update(action=action)
        except tox.exception.InvocationError:
            status = sys.exc_info()[1]
        if status:
            self.setenvstatus(venv, status)
            self.report.error(str(status))
            return False
        return True

    def installsdist(self, venv, sdist_path):
        try:
            venv.install_sdist(sdist_path)
        except tox.exception.InvocationError:
            self.setenvstatus(venv, sys.exc_info()[1])

    def sdist(self):
        if not self.config.opts.sdistonly and self.config.sdistsrc:
            self.report.info("using sdistfile %r, skipping 'sdist' activity " %
                str(self.config.sdistsrc))
            sdist_path = self.config.sdistsrc
            sdist_path = self._resolve_pkg(sdist_path)
        else:
            try:
                sdist_path = self._makesdist()
            except tox.exception.InvocationError:
                v = sys.exc_info()[1]
                self.report.error("FAIL could not package project")
                raise SystemExit(1)
            sdistfile = self.config.distshare.join(sdist_path.basename)
            if sdistfile != sdist_path:
                self.report.info("copying new sdistfile to %r" %
                    str(sdistfile))
                sdistfile.dirpath().ensure(dir=1)
                sdist_path.copy(sdistfile)
        return sdist_path

    def subcommand_test(self):
        sdist_path = self.sdist()
        if self.config.opts.sdistonly:
            return
        for venv in self.venvlist:
            self.setupenv(venv, sdist_path)
            self.runtestenv(venv, sdist_path)
        retcode = self._summary()
        return retcode

    def runtestenv(self, venv, sdist_path, redirect=False):
        if not self.config.opts.notest:
            testaction = self.newaction(venv, "runtests")
            if self.venvstatus[venv.path]:
                return
            if venv.test(testaction, redirect=redirect):
                self.setenvstatus(venv, "commands failed")
        else:
            self.setenvstatus(venv, "skipped tests")

    def _summary(self):
        action = self.newaction(None, "test summary")
        retcode = 0
        for venv in self.venvlist:
            status = self.venvstatus[venv.path]
            if status and status != "skipped tests":
                msg = "  %s: %s" %(venv.envconfig.envname, str(status))
                self.report.error(msg)
                retcode = 1
            else:
                if not status:
                    status = "commands succeeded"
                self.report.good("  %s: %s" %(venv.envconfig.envname, status))
        if not retcode:
            self.report.good("  congratulations :)")
        return retcode

    def showconfig(self):
        self.info_versions()
        self.report.keyvalue("config-file:", self.config.opts.configfile)
        self.report.keyvalue("toxinipath: ", self.config.toxinipath)
        self.report.keyvalue("toxinidir:  ", self.config.toxinidir)
        self.report.keyvalue("toxworkdir: ", self.config.toxworkdir)
        self.report.keyvalue("setupdir:   ", self.config.setupdir)
        self.report.keyvalue("distshare:  ", self.config.distshare)
        self.report.tw.line()
        for envconfig in self.config.envconfigs.values():
            self.report.line("[testenv:%s]" % envconfig.envname, bold=True)
            self.report.line("  basepython=%s" % envconfig.basepython)
            self.report.line("  envpython=%s" % envconfig.envpython)
            self.report.line("  envtmpdir=%s" % envconfig.envtmpdir)
            self.report.line("  envbindir=%s" % envconfig.envbindir)
            self.report.line("  envlogdir=%s" % envconfig.envlogdir)
            self.report.line("  changedir=%s" % envconfig.changedir)
            self.report.line("  args_are_path=%s" % envconfig.args_are_paths)
            self.report.line("  commands=")
            for command in envconfig.commands:
                self.report.line("    %s" % command)
            self.report.line("  deps=%s" % envconfig.deps)
            self.report.line("  envdir=    %s" % envconfig.envdir)
            self.report.line("  downloadcache=%s" % envconfig.downloadcache)

    def info_versions(self):
        versions = ['tox-%s' % tox.__version__]
        version = py.process.cmdexec("virtualenv --version")
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


_rex_getversion = py.std.re.compile("[\w_\-\+]+-(.*)(\.zip|\.tar.gz)")
def getversion(basename):
    m = _rex_getversion.match(basename)
    if m is None:
        return None
    version = m.group(1)
    try:
        return NormalizedVersion(version)
    except IrrationalVersionError:
        return None
