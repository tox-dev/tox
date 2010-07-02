import os, sys
import py
import re
import tox
configparser = py.builtin._tryimport("ConfigParser", "configparser")

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

def parseini(path):
    cfg = configparser.RawConfigParser()
    cfg.read(str(path))
    parser = ConfigIniParser(cfg, path)
    return parser.config

class ConfigIniParser:
    def __init__(self, cfg, toxinipath):
        self._cfg = cfg
        self.config = config = Config()
        config.toxinipath = py.path.local(toxinipath)
        config._cfg = cfg
        config.toxinidir = toxinidir = config.toxinipath.dirpath()
        reader = IniReader(self._cfg)
        reader.addsubstitions(toxinidir=config.toxinidir)
        config.toxworkdir = reader.getpath("global", "toxworkdir", 
                                           "{toxinidir}/.tox")
        reader.addsubstitions(toxworkdir=config.toxworkdir)
        config.setupdir = reader.getpath("global", "setupdir", "{toxinidir}")
        config.logdir = config.toxworkdir.join("log")
        sections = cfg.sections()
        for section in sections:
            if section.startswith(testenvprefix):
                name = section[len(testenvprefix):]
                envconfig = self._makeenvconfig(name, section, reader._subs)
                config.envconfigs[name] = envconfig
        if not config.envconfigs:
            config.envconfigs['python'] = \
                self._makeenvconfig("python", "_xz_9", reader._subs)

    def _makeenvconfig(self, name, section, subs):
        vc = VenvConfig(envname=name)
        reader = IniReader(self._cfg, fallbacksections=["testenv"])
        reader.addsubstitions(**subs)
        vc.envdir = reader.getpath(section, "envdir", "{toxworkdir}/%s" % name)
        if reader.getdefault(section, "python", None):
            raise tox.exception.ConfigError(
                "'python=' key was renamed to 'basepython='")
        vc.basepython = reader.getdefault(section, "basepython", sys.executable)
        reader.addsubstitions(envdir=vc.envdir, envname=vc.envname,
                              envbindir=vc.envbindir, envpython=vc.envpython)
        vc.envtmpdir = reader.getpath(section, "tmpdir", "{envdir}/tmp")
        reader.addsubstitions(envtmpdir=vc.envtmpdir)
        vc.argv = reader.getlist(section, "argv")
        vc.deps = reader.getlist(section, "deps")
        vc.changedir = reader.getpath(section, "changedir", "{toxinidir}")
        vc.distribute = reader.getbool(section, "distribute", False)
        downloadcache = reader.getdefault(section, "downloadcache")
        if downloadcache is None:
            downloadcache = os.environ.get("PIP_DOWNLOAD_CACHE", "")
            if not downloadcache:
                downloadcache = self.config.toxworkdir.join("_download")
        vc.downloadcache = py.path.local(downloadcache)
        return vc

class IniReader:
    def __init__(self, cfgparser, fallbacksections=None):
        self._cfg = cfgparser
        self.fallbacksections = fallbacksections or []
        self._subs = {}

    def addsubstitions(self, **kw):
        self._subs.update(kw)

    def getpath(self, section, name, defaultpath):
        return py.path.local(self.getdefault(section, name, defaultpath))

    def getlist(self, section, name, sep="\n"):
        s = self.getdefault(section, name, None)
        if s is None:
            return []
        return [x.strip() for x in s.split(sep) if x.strip()]

    def getbool(self, section, name, default=None):
        s = self.getdefault(section, name, default)
        if s is None:
            raise KeyError("no config value [%s] %s found" % (
                section, name))
        if not isinstance(s, bool):
            s = (s == "True" and True or False)
        return s

    def getdefault(self, section, name, default=None):
        try:
            x = self._cfg.get(section, name)
        except (configparser.NoSectionError, configparser.NoOptionError):
            for fallbacksection in self.fallbacksections:
                try:
                    x = self._cfg.get(fallbacksection, name)
                except (configparser.NoSectionError, configparser.NoOptionError):
                    pass
                else:
                    break
            else:
                x = default
        if x and hasattr(x, 'replace'):
            x = self._replace(x)
        return x

    def _sub(self, match):
        key = match.group(0)[1:-1]
        if key not in self._subs:
            raise tox.exception.ConfigError(
                "substitution key %r not found" % key)
        return str(self._subs[key])

    def _replace(self, x, rexpattern = re.compile("\{\w+?\}")):
        if '{' in x:
            return rexpattern.sub(self._sub, x)
        return x

