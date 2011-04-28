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

def main(args=None):
    try:
        config = parseconfig(args)
        retcode = Session(config).runcommand()
        raise SystemExit(retcode)
    except KeyboardInterrupt:
        raise SystemExit(2)

class Reporter:
    def __init__(self, config):
        self.config = config
        self.tw = py.io.TerminalWriter()

    def section(self, name):
        self.tw.sep("_", "[tox %s]" % name, bold=True)

    def action(self, msg):
        self.logline("***" + msg, bold=True)

    def info(self, msg):
        if self.config.opts.verbosity > 0:
            self.logline(msg)

    def using(self, msg):
        if self.config.opts.verbosity > 0:
            self.logline("using %s" %(msg,), bold=True)

    def popen(self, args, log, opts):
        cwd = py.path.local()
        logged_command = "%s$ %s" %(cwd, " ".join(args))
        path = None
        if log != -1: # no passthrough mode
            if log is None:
                log = self.config.logdir
            l = log.listdir()
            num = len(l)
            path = log.join("%s.log" % num)
            f = path.open('w')
            rellog = cwd.bestrelpath(path)
            logged_command += " >%s" % rellog
            f.write(logged_command+"\n")
            f.flush()
            opts.update(dict(stdout=f, stderr=subprocess.STDOUT))
        self.logline(logged_command)
        return path

    def keyboard_interrupt(self):
        self.tw.line("KEYBOARDINTERRUPT", red=True)

    def venv_installproject(self, venv, pkg):
        self.logline("installing to %s: %s" % (venv.envconfig.envname, pkg))

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
        self.logline("WARNING:" + msg)

    def error(self, msg):
        self.logline("ERROR: " + msg, red=True)

    def logline(self, msg, **opts):
        self.tw.line("[TOX] %s" % msg, **opts)

    #def log(self, msg):
    #    py.builtin.print_(msg, file=sys.stderr)


class Session:
    def __init__(self, config):
        self.config = config
        self.report = Reporter(self.config)
        self.make_emptydir(config.logdir)
        config.logdir.ensure(dir=1)
        #self.report.using("logdir %s" %(self.config.logdir,))
        self.report.using("tox.ini: %s" %(self.config.toxinipath,))
        self.venvstatus = {}
        self.venvlist = self._makevenvlist()

    def _makevenvlist(self):
        l = []
        for name in self.config.envlist:
            envconfig = self.config.envconfigs.get(name, None)
            if envconfig is None:
                self.report.error("unknown environment %r" % name)
                raise SystemExit(1)
            l.append(VirtualEnv(envconfig=envconfig, session=self))
        return l

    def runcommand(self):
        #tw.sep("-", "tox info from %s" % self.options.configfile)
        self.report.using("tox-%s from %s" %(tox.__version__, tox.__file__))
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
        self.report.action("creating sdist package")
        setup = self.config.setupdir.join("setup.py")
        if not setup.check():
            raise tox.exception.MissingFile(setup)
        self.make_emptydir(self.config.distdir)
        self.pcall([sys.executable, setup, "sdist", "--formats=zip",
                    "--dist-dir", self.config.distdir, ],
                   cwd=self.config.setupdir)
        return self.config.distdir.listdir()[0]

    def make_emptydir(self, path):
        if path.check():
            self.report.info("emptying %s" % path)
            py.std.shutil.rmtree(str(path), ignore_errors=True)
            path.mkdir()

    def setupenv(self, venv, sdist_path):
        self.venvstatus[venv.path] = 0
        try:
            status = venv.update()
        except tox.exception.InvocationError:
            status = sys.exc_info()[1]
        if status:
            self.setenvstatus(venv, status)
            self.report.error(str(status))
        elif sdist_path is not None:
            try:
                venv.install_sdist(sdist_path)
            except tox.exception.InvocationError:
                self.setenvstatus(venv, sys.exc_info()[1])

    def sdist(self):
        self.report.section("sdist")
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
                self.report.action("copying new sdistfile to %r" %
                    str(sdistfile))
                sdistfile.dirpath().ensure(dir=1)
                sdist_path.copy(sdistfile)
        return sdist_path

    def subcommand_test(self):
        sdist_path = self.sdist()
        if self.config.opts.sdistonly:
            return
        for venv in self.venvlist:
            self.report.section("testenv:%s" % venv.envconfig.envname)
            self.setupenv(venv, sdist_path)
            if self.config.opts.notest:
                self.report.info("skipping 'test' activity")
            else:
                if self.venvstatus[venv.path]:
                    continue
                if venv.test():
                    self.setenvstatus(venv, "commands failed")
        retcode = self._summary()
        return retcode

    def _summary(self):
        self.report.section("summary")
        retcode = 0
        for venv in self.venvlist:
            status = self.venvstatus[venv.path]
            if status:
                retcode = 1
                msg = "%s: %s" %(venv.envconfig.envname, str(status))
                self.report.error(msg)
            else:
                self.report.good("%s: commands succeeded" %(
                                 venv.envconfig.envname, ))
        if not retcode:
            self.report.good("congratulations :)")
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

    def pcall(self, args, log=None, cwd=None, env=None):
        if cwd is None:
            cwd = self.config.toxworkdir
        cwd.chdir()
        newargs = []
        for arg in args:
            if isinstance(arg, py.path.local):
                arg = cwd.bestrelpath(arg)
            newargs.append(arg)

        if env is None:
            env = os.environ.copy()

        opts = {'env': env}
        args = [str(x) for x in args]
        logpath = self.report.popen(newargs, log, opts)
        popen = subprocess.Popen(newargs, **opts)
        try:
            out, err = popen.communicate()
        except KeyboardInterrupt:
            self.report.keyboard_interrupt()
            popen.wait()
            raise
        ret = popen.wait()
        if ret:
            invoked = " ".join(map(str, newargs))
            if logpath:
                self.report.error("invocation failed, logfile: %s" % logpath)
                self.report.error(logpath.read())
                raise tox.exception.InvocationError(
                    "%s (see %s)" %(invoked, logpath))
            else:
                raise tox.exception.InvocationError(
                    "%r" %(invoked, ))
        return out

    def _resolve_pkg(self, pkgspec):
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
