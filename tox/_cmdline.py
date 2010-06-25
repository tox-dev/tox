"""
Automatically package and test a Python project against configurable 
Python2 and Python3 based virtual environments. Environments are
setup by using virtualenv and virtualenv3 respectively.  Configuration 
is generally done through an INI-style "tox.ini" file. 
"""
import tox
import py
import os
import sys
import argparse
import subprocess
from tox._venv import VirtualEnv
from tox._config import parseini

def main(args=None):
    try:
        parser = prepare_parse()
        opts = parser.parse_args(args or sys.argv[1:] or ["test"])
        opts.configfile = py.path.local(opts.configfile)
        if not opts.configfile.check():
            feedback("config file %r does not exist" %(
                str(opts.configfile)), sysexit=True)
        config = parseini(opts.configfile)
        config.opts = opts
        Session(config).runcommand()
    except KeyboardInterrupt:
        raise SystemExit(2)

def feedback(msg, sysexit=False):
    py.builtin.print_("ERROR: " + msg, file=sys.stderr)
    if sysexit:
        raise SystemExit(1)

class VersionAction(argparse.Action):
    def __call__(self, *args, **kwargs):
        py.builtin.print_("%s imported from %s" %(tox.__version__,
                          tox.__file__))
        raise SystemExit(0)

def prepare_parse():
    parser = argparse.ArgumentParser(description=__doc__,)
        #formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--version", nargs=0, action=VersionAction, 
        dest="version",
        help="report version information to stdout.")
    parser.add_argument("--showconfig", action="store_true", dest="showconfig", 
        help="show configuration information. ")
    parser.add_argument("-c", action="store", default="tox.ini", 
        dest="configfile",
        help="use the specified config file.")
    parser.add_argument("-e", "--env", action="append", dest="envlist", 
        metavar="ENV",
        help="work against specified environment (multi-allowed).")
    parser.add_argument("testpath", nargs="*", help="a path to a test")
    return parser

class Reporter:
    def __init__(self, config):
        self.config = config 
        self.tw = py.io.TerminalWriter()

    def section(self, name):
        self.tw.sep("=", name, bold=True)

    def action(self, msg):
        self.tw.line("***" + msg, bold=True)

    def using(self, msg):
        self.tw.line("using %s" %(msg,), bold=True)

    def popen(self, args, log, opts):
        cwd = py.path.local()
        logged_command = "%s$ %s" %(cwd, " ".join(args))
        if log != -1: # no passthrough mode 
            if log is None:
                log = self.config.logdir
            l = log.listdir()
            num = len(l)
            path = log.join("%s.log" % num)
            f = open(str(path), 'w')
            rellog = cwd.bestrelpath(path)
            logged_command += " >%s" % rellog
            f.write(logged_command+"\n")
            opts.update(dict(stdout=f, stderr=subprocess.STDOUT))
        self.tw.line(logged_command)

    def keyboard_interrupt(self):
        self.tw.line("KEYBOARDINTERRUPT", red=True)

    def venv_installproject(self, venv, pkg):
        self.tw.line("installing to %s: %s" % (venv.envconfig.name, pkg))

    def keyvalue(self, name, value):
        if name.endswith(":"):
            name += " "
        self.tw.write(name, bold=True)
        self.tw.write(value)
        self.tw.line()

    def line(self, msg, **opts):
        self.tw.line(msg, **opts)

    def good(self, msg):
        self.tw.line(msg, green=True)

    def error(self, msg):
        self.tw.line("ERROR: " + msg, red=True)

    def log(self, msg):
        py.builtin.print_(msg, file=sys.stderr)

        
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
        
    def runcommand(self):
        #tw.sep("-", "tox info from %s" % self.options.configfile)
        self.report.using("tox-%s from %s" %(tox.__version__, tox.__file__))
        if self.config.opts.showconfig:
            self.subcommand_config()
        else:
            self.subcommand_test()

    def _copyfiles(self, srcdir, pathlist, destdir):
        for relpath in pathlist:
            src = srcdir.join(relpath)
            if not src.check():
                self.report.error("missing source file: %s" %(src,))
                raise SystemExit(1)
            target = destdir.join(relpath)
            target.dirpath().ensure(dir=1)
            src.copy(target)

    def _makevenvlist(self):
        try:
            envlist = self.config.opts.envlist
        except AttributeError:
            envlist = None
        if not envlist:
            envlist = self.config.envconfigs.keys()
        l = []
        for name in envlist:
            envconfig = self.config.envconfigs.get(name, None)
            if envconfig is None:
                self.report.error("unknown environment %r" % name)
                raise SystemExit(1)
            l.append(VirtualEnv(envconfig=envconfig, session=self))
        return l

    def setenvstatus(self, venv, msg):
        self.venvstatus[venv.path] = msg 

    def build_and_install(self, venv):
        sdist_path = self.get_fresh_sdist()
        #self.report.venv_installproject(venv, sdist_path)
        try:
            venv.install([sdist_path])
        except tox.exception.InvocationError:
            self.setenvstatus(venv, "FAIL could not install package")

    def _makesdist(self):
        self.report.action("creating sdist package")
        setup = self.config.packagedir.join("setup.py")
        if not setup.check():
            raise MissingFile(setup)
        distdir = self.config.toxdir.join("dist")
        if distdir.check():
            distdir.remove() 
        self.pcall([sys.executable, setup, "sdist", "--dist-dir", distdir],
                   cwd=self.config.packagedir)
        return distdir.listdir()[0]

    def get_fresh_sdist(self):
        try:
            return self._sdistpath
        except AttributeError:
            try:
                self._sdistpath = x = self._makesdist()
            except tox.exception.InvocationError:
                v = sys.exc_info()[1]
                self.report.error("FAIL could not package project")
                return None
            return x

    def make_emptydir(self, path):
        if path.check():
            py.std.shutil.rmtree(str(path), ignore_errors=True)
            path.mkdir()

    def setupenv(self):
        self.report.section("setupenv")
        x = self.get_fresh_sdist() # do it ahead for nicer reporting
        if x is None:
            self.report.error("aborting tox run")
            raise SystemExit(1)
        for venv in self.venvlist:
            self.venvstatus[venv.path] = 0
            if venv.path.join("VALID").check():
                self.report.action("preparing virtualenv %s - "
                    "reusing existing" %
                    venv.envconfig.name)
            else:
                self.report.action("preparing fresh virtualenv %s" %
                    venv.envconfig.name)
                self.make_emptydir(venv.path)
                try:
                    venv.create()
                except tox.exception.MissingInterpreter:
                    v = sys.exc_info()[1]
                    self.setenvstatus(venv, 
                        "FAIL could not create: %s" % (str(v)))
                    continue
                try:
                    venv.install(venv.envconfig.deps)
                except tox.exception.InvocationError:
                    v = sys.exc_info()[1]
                    self.setenvstatus(venv, 
                        "FAIL could not install deps %r" %
                            ",".join(venv.envconfig.deps))
                    continue
            venv.path.ensure("VALID")
            self.build_and_install(venv)

    def subcommand_test(self):
        self.setupenv()
        self.report.section("test")
        for venv in self.venvlist:
            if self.venvstatus[venv.path]:
                continue
            if venv.test(cwd=venv.envconfig.changedir):
                self.setenvstatus(venv, "tests failed")
        retcode = self._summary()
        return retcode

    def _summary(self):
        self.report.section("tox summary")
        retcode = 0
        for venv in self.venvlist:
            status = self.venvstatus[venv.path]
            if status:
                retcode = 1
                self.report.error("%s: %s" %(venv.envconfig.name, status))
            else:
                self.report.good("%s: no failures" %(venv.envconfig.name, ))
        if not retcode:
            self.report.good("congrats :)")
        return retcode 

    def subcommand_config(self):
        self.info_versions()
        self.report.keyvalue("config-file:", self.config.opts.configfile)
        self.report.keyvalue("package directory:", self.config.packagedir)
        self.report.keyvalue("toxdir:", self.config.toxdir)
        self.report.tw.line()
        for envconfig in self.config.envconfigs.values():
            self.report.line("[testenv:%s]" % envconfig.name, bold=True)
            self.report.line("    python=%s" % envconfig.python)
            self.report.line("    cmdargs=%s" % envconfig.cmdargs)
            self.report.line("    deps=%s" % envconfig.deps)
            self.report.line("    envdir=    %s" % envconfig.envdir)
            self.report.line("    downloadcache=%s" % envconfig.downloadcache)

    def info_versions(self):
        versions = ['tox-%s' % tox.__version__]
        for tool in ('virtualenv', 'virtualenv3'):
            version = py.process.cmdexec("%s --version" % tool)
            versions.append("%s-%s" %(tool, version.strip()))
        self.report.keyvalue("tool-versions:", " ".join(versions))
   
    def pcall(self, args, log=None, cwd=None):
        if cwd is None:
            cwd = self.config.toxdir
        cwd.chdir()
        newargs = []
        for arg in args:
            if isinstance(arg, py.path.local):
                arg = cwd.bestrelpath(arg)
            newargs.append(arg)
           
        opts = {} 
        args = [str(x) for x in args]
        self.report.popen(newargs, log, opts)
        popen = subprocess.Popen(newargs, **opts)
        try:
            out, err = popen.communicate()
        except KeyboardInterrupt:
            self.report.keyboard_interrupt()
            popen.wait()
            raise
        ret = popen.wait()
        if ret:
            raise InvocationError(
                "error %d while calling %r:\n%s" %(ret, args, err))
        return out

class InvocationError(Exception):
    """ an error while invoking a script. """
class MissingFile(Exception):
    """ an error while invoking a script. """

