import os, sys
import py
import re
import tox
import argparse

defaultenvs = {'jython': 'jython', 'pypy': 'pypy-c'}
for _name in "py24,py25,py26,py27,py30,py31,py32".split(","):
    defaultenvs[_name] = "python%s.%s" %(_name[2], _name[3])

def parseconfig(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = prepare_parse()
    opts = parser.parse_args(args)
    config = Config()
    config.opts = opts
    parseini(config)
    return config

def feedback(msg, sysexit=False):
    py.builtin.print_("ERROR: " + msg, file=sys.stderr)
    if sysexit:
        raise SystemExit(1)

class VersionAction(argparse.Action):
    def __call__(self, *args, **kwargs):
        py.builtin.print_("%s imported from %s" %(tox.__version__,
                          tox.__file__))
        raise SystemExit(0)

class CountAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if hasattr(namespace, self.dest):
            setattr(namespace, self.dest, int(getattr(namespace, self.dest))+1)
        else:
            setattr(namespace, self.dest, 0)

def prepare_parse():
    parser = argparse.ArgumentParser(description=__doc__,)
        #formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--version", nargs=0, action=VersionAction,
        dest="version",
        help="report version information to stdout.")
    parser.add_argument("-v", nargs=0, action=CountAction, default=0,
        dest="verbosity",
        help="increase verbosity of reporting output.")
    parser.add_argument("--showconfig", action="store_true", dest="showconfig",
        help="show configuration information. ")
    parser.add_argument("-c", action="store", default="tox.ini",
        dest="configfile",
        help="use the specified config file.")
    parser.add_argument("-e", action="store", dest="env",
        metavar="envlist",
        help="work against specified environments (ALL selects all).")
    parser.add_argument("--notest", action="store_true", dest="notest",
        help="skip invoking test commands.")
    parser.add_argument("--sdistonly", action="store_true", dest="sdistonly",
        help="only perform the sdist activity.")
    parser.add_argument("--indexserver", action="store", dest="indexserver",
        default=None, metavar="URL",
        help="indexserver for installing deps (default pypi python.org"),
    parser.add_argument("-r", "--recreate", action="store_true",
        dest="recreate",
        help="recreate virtual environments")
    parser.add_argument("args", nargs="*",
        help="additional arguments available to command positional substition")
    return parser

class Config:
    def __init__(self):
        self.envconfigs = {}
        self.invocationcwd = py.path.local()

class ConfigError(Exception):
    """ error in tox configuration. """

class VenvConfig:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    @property
    def envbindir(self):
        if sys.platform == "win32" and "jython" not in self.basepython:
            return self.envdir.join("Scripts")
        else:
            return self.envdir.join("bin")

    @property
    def envpython(self):
        if "jython" in str(self.basepython):
            name = "jython"
        else:
            name = "python"
        return self.envbindir.join(name)

testenvprefix = "testenv:"

class parseini:
    def __init__(self, config):
        config.opts.configfile = py.path.local(config.opts.configfile)
        config.toxinipath = config.opts.configfile
        config.toxinidir = toxinidir = config.toxinipath.dirpath()
        if not config.toxinipath.check():
            feedback("toxini file %r does not exist" %(
                str(config.toxinipath)), sysexit=True)
        self._cfg = py.iniconfig.IniConfig(config.toxinipath)
        config._cfg = self._cfg
        self.config = config
        ctxname = getcontextname()
        if ctxname == "hudson":
            reader = IniReader(self._cfg, fallbacksections=['tox'])
            toxsection = "tox:%s" % ctxname
            distshare_default = "{toxworkdir}/distshare"
        elif not ctxname:
            reader = IniReader(self._cfg)
            toxsection = "tox"
            distshare_default = "{homedir}/.tox/distshare"
        else:
            raise ValueError("invalid context")

        config.homedir = py.path.local._gethomedir()
        reader.addsubstitions(toxinidir=config.toxinidir,
                              homedir=config.homedir)
        config.toxworkdir = reader.getpath(toxsection, "toxworkdir",
                                           "{toxinidir}/.tox")

        # determine indexserver dictionary
        config.indexserver = d = {}
        for line in reader.getlist(toxsection, "indexserver"):
            name, value = line.strip().split(None, 1)
            d.setdefault(name, value)
        if config.opts.indexserver:
            d['default'] = config.opts.indexserver
        else:
            d.setdefault('default', None)
            
        reader.addsubstitions(toxworkdir=config.toxworkdir)
        config.distdir = reader.getpath(toxsection, "distdir",
                                           "{toxworkdir}/dist")
        reader.addsubstitions(distdir=config.distdir)
        config.distshare = reader.getpath(toxsection, "distshare",
                                          distshare_default)
        reader.addsubstitions(distshare=config.distshare)
        config.sdistsrc = reader.getpath(toxsection, "sdistsrc", None)
        config.setupdir = reader.getpath(toxsection, "setupdir", "{toxinidir}")
        config.logdir = config.toxworkdir.join("log")
        for sectionwrapper in self._cfg:
            section = sectionwrapper.name
            if section.startswith(testenvprefix):
                name = section[len(testenvprefix):]
                envconfig = self._makeenvconfig(name, section, reader._subs,
                    config)
                config.envconfigs[name] = envconfig
        if not config.envconfigs:
            config.envconfigs['python'] = \
                self._makeenvconfig("python", "_xz_9", reader._subs, config)
        config.envlist = self._getenvlist(reader, toxsection)
        for name in config.envlist:
            if name not in config.envconfigs:
                if name in defaultenvs:
                    config.envconfigs[name] = \
                self._makeenvconfig(name, "_xz_9", reader._subs, config)

    def _makeenvconfig(self, name, section, subs, config):
        vc = VenvConfig(envname=name)
        reader = IniReader(self._cfg, fallbacksections=["testenv"])
        reader.addsubstitions(**subs)
        vc.envdir = reader.getpath(section, "envdir", "{toxworkdir}/%s" % name)
        vc.args_are_paths = reader.getbool(section, "args_are_paths", True)
        if reader.getdefault(section, "python", None):
            raise tox.exception.ConfigError(
                "'python=' key was renamed to 'basepython='")
        if name in defaultenvs:
            bp = defaultenvs[name]
        else:
            bp = sys.executable
        vc.basepython = reader.getdefault(section, "basepython", bp)
        reader.addsubstitions(envdir=vc.envdir, envname=vc.envname,
                              envbindir=vc.envbindir, envpython=vc.envpython)
        vc.envtmpdir = reader.getpath(section, "tmpdir", "{envdir}/tmp")
        vc.envlogdir = reader.getpath(section, "envlogdir", "{envdir}/log")
        reader.addsubstitions(envlogdir=vc.envlogdir, envtmpdir=vc.envtmpdir)
        vc.changedir = reader.getpath(section, "changedir", "{toxinidir}")
        if config.opts.recreate:
            vc.recreate = True
        else:
            vc.recreate = reader.getbool(section, "recreate", False)
        args = config.opts.args
        if args:
            if vc.args_are_paths:
                args = []
                for arg in config.opts.args:
                    origpath = config.invocationcwd.join(arg, abs=True)
                    if origpath.check():
                        arg = vc.changedir.bestrelpath(origpath)
                    args.append(arg)
            reader.addsubstitions(args)
        vc.commands = reader.getargvlist(section, "commands")
        vc.deps = [x.replace("/", os.sep) for x in reader.getlist(section, "deps")]
        vc.distribute = reader.getbool(section, "distribute", True)
        vc.sitepackages = reader.getbool(section, "sitepackages", False)
        downloadcache = reader.getdefault(section, "downloadcache")
        if downloadcache is None:
            downloadcache = os.environ.get("PIP_DOWNLOAD_CACHE", "")
            if not downloadcache:
                downloadcache = self.config.toxworkdir.join("_download")
        vc.downloadcache = py.path.local(downloadcache)
        return vc

    def _getenvlist(self, reader, toxsection):
        env = self.config.opts.env
        if not env:
            env = os.environ.get("TOXENV", None)
            if not env:
                envlist = reader.getlist(toxsection, "envlist", sep=",")
                if not envlist:
                    envlist = self.config.envconfigs.keys()
                return envlist
        if env == "ALL":
            envlist = list(self.config.envconfigs)
            envlist.sort()
        else:
            envlist = env.split(",")
        return envlist

class IniReader:
    def __init__(self, cfgparser, fallbacksections=None):
        self._cfg = cfgparser
        self.fallbacksections = fallbacksections or []
        self._subs = {}

    def addsubstitions(self, _posargs=None, **kw):
        self._subs.update(kw)
        if _posargs:
            self._subs['_posargs'] = _posargs

    def getpath(self, section, name, defaultpath):
        toxinidir = self._subs['toxinidir']
        path = self.getdefault(section, name, defaultpath)
        if path is None:
            return path
        return toxinidir.join(path, abs=True)

    def getlist(self, section, name, sep="\n"):
        s = self.getdefault(section, name, None)
        if s is None:
            return []
        return [x.strip() for x in s.split(sep) if x.strip()]

    def getargvlist(self, section, name):
        s = self.getdefault(section, name, '', replace=False)
        #if s is None:
        #    raise tox.exception.ConfigError(
        #        "no command list %r defined in section [%s]" %(name, section))
        commandlist = []
        current_command = ""
        for line in s.split("\n"):
            line = line.rstrip()
            i = line.find("#")
            if i != -1:
                line = line[:i].rstrip()
            if not line:
                continue
            if line.endswith("\\"):
                current_command += " " + line[:-1]
                continue
            current_command += line
            commandlist.append(self._processcommand(current_command))
            current_command = ""
        else:
            if current_command:
                raise tox.exception.ConfigError(
                    "line-continuation for [%s] %s ends nowhere" %
                    (section, name))
        return commandlist

    def _processcommand(self, command):
        posargs = self._subs.get('_posargs', None)
        if posargs:
            posargstring = " ".join(posargs)
            command = re.sub("\[.*\]", lambda m: posargstring, command)
        else:
            command = command.replace("[", "").replace("]", "")
        argv = [self._replace(x) for x in command.split()]
        return argv

    def getbool(self, section, name, default=None):
        s = self.getdefault(section, name, default)
        if s is None:
            raise KeyError("no config value [%s] %s found" % (
                section, name))
        if not isinstance(s, bool):
            if s.lower() == "true":
                s = True
            elif s.lower() == "false":
                s = False
            else:
                raise tox.exception.ConfigError(
                    "boolean value %r needs to be 'True' or 'False'")
        return s

    def getdefault(self, section, name, default=None, replace=True):
        try:
            x = self._cfg[section][name]
        except KeyError:
            for fallbacksection in self.fallbacksections:
                try:
                    x = self._cfg[fallbacksection][name]
                except KeyError:
                    pass
                else:
                    break
            else:
                x = default
        if replace and x and hasattr(x, 'replace'):
            x = self._replace(x)
        #print "getdefault", section, name, "returned", repr(x)
        return x

    def _sub(self, match):
        key = match.group(0)[1:-1]
        if key.startswith("env:"):
            envkey = key[4:]
            if envkey not in os.environ:
                raise tox.exception.ConfigError(
                    "substitution %r: %r not found in environment" %
                    (key, envkey))
            return os.environ[envkey]
        if key not in self._subs:
            raise tox.exception.ConfigError(
                "substitution key %r not found" % key)
        return str(self._subs[key])

    def _replace(self, x, rexpattern = re.compile("\{.+?\}")):
        if '{' in x:
            return rexpattern.sub(self._sub, x)
        return x


def getcontextname():
    if 'HUDSON_URL' in os.environ:
        return 'hudson'
    return None
