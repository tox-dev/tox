import os, sys
import py
configparser = py.builtin._tryimport("ConfigParser", "configparser")

class Config:
    def __init__(self):
        self.envconfigs = {}

class ConfigError(Exception):
    """ error in tox configuration. """

class VenvConfig:
    def __init__(self, **kw):
        self.__dict__.update(kw)

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
        toxinidir = config.toxinipath.dirpath()
        reader = IniReader(self._cfg)
        config.toxdir = reader.getpath("global", "toxdir", toxinidir, ".tox")
        config.packagedir = reader.getpath("global", "packagedir", toxinidir)
        config.logdir = config.toxdir.join("log")
        sections = cfg.sections()
        for section in sections:
            if section.startswith(testenvprefix):
                name = section[len(testenvprefix):]
                config.envconfigs[name] = self._makeenvconfig(name, section)
        if not config.envconfigs:
            config.envconfigs['python'] = self._makeenvconfig("python", "_xz_9")

    def _makeenvconfig(self, name, section):
        vc = VenvConfig(name=name)
        vc.envdir = self.config.toxdir.join(name)
        reader = IniReader(self._cfg, fallbacksections=["test"])
        vc.envtmpdir = reader.getpath(section, "tmpdir", vc.envdir.join("tmp"))
        reader.addsubstitions(envname=vc.name, envtmpdir=vc.envtmpdir)
        vc.python = reader.getdefault(section, "python", None)
        vc.cmdargs = reader.getlist(section, "cmdargs")
        vc.deps = reader.getlist(section, "deps")
        vc.changedir = reader.getpath(section, "changedir", self.config.packagedir)
        downloadcache = reader.getdefault(section, "downloadcache")
        if downloadcache is None:
            downloadcache = os.environ.get("PIP_DOWNLOAD_CACHE", "")
            if not downloadcache:
                downloadcache = self.config.toxdir.join("_download")
        vc.downloadcache = py.path.local(downloadcache)
        return vc

class IniReader:
    def __init__(self, cfgparser, fallbacksections=None):
        self._cfg = cfgparser
        self.fallbacksections = fallbacksections or []
        self._subs = {}

    def addsubstitions(self, **kw):
        self._subs.update(kw)

    def getpath(self, section, name, basedir, basename=None):
        basename = self.getdefault(section, name, basename)
        if basename is None:
            return basedir
        return basedir.join(basename, abs=True)

    def getlist(self, section, name, sep="\n"):
        s = self.getdefault(section, name, None)
        if s is None:
            return []
        return [x.strip() for x in s.split(sep) if x.strip()]

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
        if self._subs and x:
            for name, value in self._subs.items():
                substname = "{%s}" % name
                x = x.replace(substname, str(value))
        return x

