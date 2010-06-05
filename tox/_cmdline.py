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
    py.builtin.print_(msg, file=sys.stderr)

def prepare_parse():
    parser = argparse.ArgumentParser(description=__doc__,)
        #formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", action="store", default="tox.ini", 
        dest="configfile",
        help="use the specified config file.")
    subparsers = parser.add_subparsers(title="subcommands")

    # common options
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-e", "--env", action="append", dest="env", 
        help="work against specified environment (multi-allowed).")

    # config subcommand
    parser_info = subparsers.add_parser("config", 
        help="show meta versioning and configuration information.", 
        parents=(common,))
    parser_info.set_defaults(subcommand="config")

    # package subcommand
    #parser_package = subparsers.add_parser("package", parents=(common,),
    #    help="package project for distribution and testing. ")
    #parser_package.set_defaults(func=self.package)

    # test subcommand
    parser_test = subparsers.add_parser("test", parents=(common,),
        help="run tests in virtual environments.")
    parser_test.add_argument("testpath", nargs="*", help="a path to a test")
    parser_test.set_defaults(subcommand="test")
    return parser

class Reporter:
    def __init__(self, config):
        self.config = config 
        self.tw = py.io.TerminalWriter()

    def section(self, name):
        self.tw.sep("=", name, bold=True)

    def popen(self, args):
        cwd = os.getcwd()
        self.tw.line("%s$ %s" %(cwd, " ".join(args)))

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

    def error(self, msg):
        self.tw.line(msg, red=True)

    def log(self, msg):
        py.builtin.print_(msg, file=sys.stderr)

        
class Session:
    def __init__(self, config):
        self.config = config
        
    def runcommand(self):
        #tw.sep("-", "tox info from %s" % self.options.configfile)
        self.report = Reporter(self.config)
        getattr(self, "subcommand_" + self.config.opts.subcommand)()

    def getsdist(self, venv):
        destdir = self.config.toxdir.join("_makepackage")
        distdir = destdir.join("dist")

        self.report.line("copying package files")
        srcdir = self.config.projdir 
        for relpath in self.config.getpackagelist():
            src = srcdir.join(relpath)
            if not src.check():
                self.report.error("missing source file: %s" %(src,))
                raise SystemExit(1)
            target = destdir.join(relpath)
            target.dirpath().ensure(dir=1)
            src.copy(target)
        
        old = destdir.chdir()
        try:
            if distdir.check():
                distdir.remove()
            py = destdir.bestrelpath(venv.getcommandpath("python"))
            self.pcall([py, "setup.py", "sdist"])
            return distdir.listdir()[0]
        finally:
            old.chdir()

    def _gettestenvs(self, envlist):
        for envconfig in self.config.envconfigs.values():
            if not envlist or envconfig.name in envlist:
                yield VirtualEnv(envconfig=envconfig, project=self)

    def build_and_install(self, venv):
        sdist_path = self.getsdist(venv)
        #self.report.venv_installproject(venv, sdist_path)
        venv.install([sdist_path])

    def setupenv(self, envlist):
        self.report.section("setupenv")
        for venv in self._gettestenvs(envlist):
            venv.create()
            venv.install(venv.envconfig.deps)
            self.build_and_install(venv)

    def subcommand_test(self):
        envlist = self.config.opts.env
        self.setupenv(envlist)
        self.report.section("test")
        somefailed = False
        for venv in self._gettestenvs(envlist):
            if venv.test():
                somefailed = True
        return somefailed

    def subcommand_config(self):
        self.info_versions()
        self.report.keyvalue("config-file:", self.config.opts.configfile)
        self.report.keyvalue("project directory:", self.config.projdir)
        self.report.keyvalue("toxdir:", self.config.toxdir)
        self.report.tw.line()
        for envconfig in self.config.envconfigs.values():
            self.report.line("[testenv:%s]" % envconfig.name, bold=True)
            self.report.line("    python=%s" % envconfig.python)
            self.report.line("    command=%s" % envconfig.command)
            self.report.line("    deps=%s" % envconfig.deps)
            self.report.line("    envdir=    %s" % envconfig.envdir)
            self.report.line("    downloadcache=%s" % envconfig.downloadcache)

    def info_versions(self):
        versions = ['tox-%s' % tox.__version__]
        for tool in ('virtualenv', 'virtualenv3'):
            version = py.process.cmdexec("%s --version" % tool)
            versions.append("%s-%s" %(tool, version.strip()))
        self.report.keyvalue("tool-versions:", " ".join(versions))
   
    def pcall(self, args, out=None):
        opts = dict(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if out == "passthrough":
            opts = {}
        args = [str(x) for x in args]
        #if os.path.isabs(args[0]):
        #    self.config.toxdir.chdir()
        #    args[0] = py.path.local(args[0]).bestrelto(self.config.toxdir)
        self.report.popen(args)
        popen = subprocess.Popen(args, **opts)
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

