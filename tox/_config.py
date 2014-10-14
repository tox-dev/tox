import argparse
import os
import random
import sys
import re
import shlex
import string
import pkg_resources
import itertools

from tox.interpreters import Interpreters

import py

import tox

iswin32 = sys.platform == "win32"

default_factors = {'jython': 'jython', 'pypy': 'pypy', 'pypy3': 'pypy3',
                   'py': sys.executable}
for version in '24,25,26,27,30,31,32,33,34'.split(','):
    default_factors['py' + version] = 'python%s.%s' % tuple(version)

def parseconfig(args=None, pkg=None):
    if args is None:
        args = sys.argv[1:]
    parser = prepare_parse(pkg)
    opts = parser.parse_args(args)
    config = Config()
    config.option = opts
    basename = config.option.configfile
    if os.path.isabs(basename):
        inipath = py.path.local(basename)
    else:
        for path in py.path.local().parts(reverse=True):
            inipath = path.join(basename)
            if inipath.check():
                break
        else:
            feedback("toxini file %r not found" %(basename), sysexit=True)
    try:
        parseini(config, inipath)
    except tox.exception.InterpreterNotFound:
        exn = sys.exc_info()[1]
        # Use stdout to match test expectations
        py.builtin.print_("ERROR: " + str(exn))
    return config

def feedback(msg, sysexit=False):
    py.builtin.print_("ERROR: " + msg, file=sys.stderr)
    if sysexit:
        raise SystemExit(1)

class VersionAction(argparse.Action):
    def __call__(self, argparser, *args, **kwargs):
        name = argparser.pkgname
        mod = __import__(name)
        version = mod.__version__
        py.builtin.print_("%s imported from %s" %(version, mod.__file__))
        raise SystemExit(0)

class CountAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if hasattr(namespace, self.dest):
            setattr(namespace, self.dest, int(getattr(namespace, self.dest))+1)
        else:
            setattr(namespace, self.dest, 0)

def prepare_parse(pkgname):
    parser = argparse.ArgumentParser(description=__doc__,)
        #formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.pkgname = pkgname
    parser.add_argument("--version", nargs=0, action=VersionAction,
        dest="version",
        help="report version information to stdout.")
    parser.add_argument("-v", nargs=0, action=CountAction, default=0,
        dest="verbosity",
        help="increase verbosity of reporting output.")
    parser.add_argument("--showconfig", action="store_true",
        help="show configuration information for all environments. ")
    parser.add_argument("-l", "--listenvs", action="store_true",
        dest="listenvs", help="show list of test environments")
    parser.add_argument("-c", action="store", default="tox.ini",
        dest="configfile",
        help="use the specified config file name.")
    parser.add_argument("-e", action="append", dest="env",
        metavar="envlist",
        help="work against specified environments (ALL selects all).")
    parser.add_argument("--notest", action="store_true", dest="notest",
        help="skip invoking test commands.")
    parser.add_argument("--sdistonly", action="store_true", dest="sdistonly",
        help="only perform the sdist packaging activity.")
    parser.add_argument("--installpkg", action="store", default=None,
        metavar="PATH",
        help="use specified package for installation into venv, instead of "
             "creating an sdist.")
    parser.add_argument("--develop", action="store_true", dest="develop",
        help="install package in the venv using 'setup.py develop' via "
             "'pip -e .'")
    parser.add_argument("--set-home", action="store_true", dest="sethome",
        help="(experimental) force creating a new $HOME for each test "
             "environment and create .pydistutils.cfg|pip.conf files "
             "if index servers are specified with tox. ")
    parser.add_argument('-i', action="append",
        dest="indexurl", metavar="URL",
        help="set indexserver url (if URL is of form name=url set the "
        "url for the 'name' indexserver, specifically)")
    parser.add_argument("-r", "--recreate", action="store_true",
        dest="recreate",
        help="force recreation of virtual environments")
    parser.add_argument("--result-json", action="store",
        dest="resultjson", metavar="PATH",
        help="write a json file with detailed information about "
             "all commands and results involved.  This will turn off "
             "pass-through output from running test commands which is "
             "instead captured into the json result file.")
    # We choose 1 to 4294967295 because it is the range of PYTHONHASHSEED.
    parser.add_argument("--hashseed", action="store",
        metavar="SEED", default=None,
        help="set PYTHONHASHSEED to SEED before running commands.  "
             "Defaults to a random integer in the range [1, 4294967295] "
             "([1, 1024] on Windows). "
             "Passing 'noset' suppresses this behavior.")
    parser.add_argument("--force-dep", action="append",
        metavar="REQ", default=None,
        help="Forces a certain version of one of the dependencies "
             "when configuring the virtual environment. REQ Examples "
             "'pytest<2.7' or 'django>=1.6'.")
    parser.add_argument("--sitepackages", action="store_true",
        help="override sitepackages setting to True in all envs")
    parser.add_argument("--skip-missing-interpreters", action="store_true",
        help="don't fail tests for missing interpreters")

    parser.add_argument("args", nargs="*",
        help="additional arguments available to command positional substitution")
    return parser

class Config(object):
    def __init__(self):
        self.envconfigs = {}
        self.invocationcwd = py.path.local()
        self.interpreters = Interpreters()

    @property
    def homedir(self):
        homedir = get_homedir()
        if homedir is None:
            homedir = self.toxinidir  # XXX good idea?
        return homedir

class VenvConfig:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    @property
    def envbindir(self):
        if (sys.platform == "win32" and "jython" not in self.basepython
                                    and "pypy" not in self.basepython):
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

    # no @property to avoid early calling (see callable(subst[key]) checks)
    def envsitepackagesdir(self):
        self.getsupportedinterpreter()  # for throwing exceptions
        x = self.config.interpreters.get_sitepackagesdir(
                info=self._basepython_info,
                envdir=self.envdir)
        return x

    def getsupportedinterpreter(self):
        if sys.platform == "win32" and self.basepython and \
                "jython" in self.basepython:
            raise tox.exception.UnsupportedInterpreter(
                "Jython/Windows does not support installing scripts")
        info = self.config.interpreters.get_info(self.basepython)
        if not info.executable:
            raise tox.exception.InterpreterNotFound(self.basepython)
        if not info.version_info:
            raise tox.exception.InvocationError(
                'Failed to get version_info for %s: %s' % (info.name, info.err))
        if info.version_info < (2,6):
            raise tox.exception.UnsupportedInterpreter(
                "python2.5 is not supported anymore, sorry")
        return info.executable

testenvprefix = "testenv:"

def get_homedir():
    try:
        return py.path.local._gethomedir()
    except Exception:
        return None

def make_hashseed():
    max_seed = 4294967295
    if sys.platform == 'win32':
        max_seed = 1024
    return str(random.randint(1, max_seed))

class parseini:
    def __init__(self, config, inipath):
        config.toxinipath = inipath
        config.toxinidir = config.toxinipath.dirpath()

        self._cfg = py.iniconfig.IniConfig(config.toxinipath)
        config._cfg = self._cfg
        self.config = config
        ctxname = getcontextname()
        if ctxname == "jenkins":
            reader = IniReader(self._cfg, fallbacksections=['tox'])
            toxsection = "tox:%s" % ctxname
            distshare_default = "{toxworkdir}/distshare"
        elif not ctxname:
            reader = IniReader(self._cfg)
            toxsection = "tox"
            distshare_default = "{homedir}/.tox/distshare"
        else:
            raise ValueError("invalid context")

        if config.option.hashseed is None:
            hashseed = make_hashseed()
        elif config.option.hashseed == 'noset':
            hashseed = None
        else:
            hashseed = config.option.hashseed
        config.hashseed = hashseed

        reader.addsubstitutions(toxinidir=config.toxinidir,
                                homedir=config.homedir)
        config.toxworkdir = reader.getpath(toxsection, "toxworkdir",
                                           "{toxinidir}/.tox")
        config.minversion = reader.getdefault(toxsection, "minversion", None)

        if not config.option.skip_missing_interpreters:
            config.option.skip_missing_interpreters = \
                reader.getbool(toxsection, "skip_missing_interpreters", False)

        # determine indexserver dictionary
        config.indexserver = {'default': IndexServerConfig('default')}
        prefix = "indexserver"
        for line in reader.getlist(toxsection, prefix):
            name, url = map(lambda x: x.strip(), line.split("=", 1))
            config.indexserver[name] = IndexServerConfig(name, url)

        override = False
        if config.option.indexurl:
            for urldef in config.option.indexurl:
                m = re.match(r"\W*(\w+)=(\S+)", urldef)
                if m is None:
                    url = urldef
                    name = "default"
                else:
                    name, url = m.groups()
                    if not url:
                        url = None
                if name != "ALL":
                    config.indexserver[name].url = url
                else:
                    override = url
        # let ALL override all existing entries
        if override:
            for name in config.indexserver:
                config.indexserver[name] = IndexServerConfig(name, override)

        reader.addsubstitutions(toxworkdir=config.toxworkdir)
        config.distdir = reader.getpath(toxsection, "distdir",
                                           "{toxworkdir}/dist")
        reader.addsubstitutions(distdir=config.distdir)
        config.distshare = reader.getpath(toxsection, "distshare",
                                          distshare_default)
        reader.addsubstitutions(distshare=config.distshare)
        config.sdistsrc = reader.getpath(toxsection, "sdistsrc", None)
        config.setupdir = reader.getpath(toxsection, "setupdir", "{toxinidir}")
        config.logdir = config.toxworkdir.join("log")

        config.envlist, all_envs = self._getenvdata(reader, toxsection)

        # configure testenvs
        known_factors = self._list_section_factors("testenv")
        known_factors.update(default_factors)
        known_factors.add("python")
        for name in all_envs:
            section = testenvprefix + name
            factors = set(name.split('-'))
            if section in self._cfg or factors <= known_factors:
                config.envconfigs[name] = \
                    self._makeenvconfig(name, section, reader._subs, config)

        all_develop = all(name in config.envconfigs
                          and config.envconfigs[name].develop
                          for name in config.envlist)

        config.skipsdist = reader.getbool(toxsection, "skipsdist", all_develop)

    def _list_section_factors(self, section):
        factors = set()
        if section in self._cfg:
            for _, value in self._cfg[section].items():
                exprs = re.findall(r'^([\w{}\.,-]+)\:\s+', value, re.M)
                factors.update(*mapcat(_split_factor_expr, exprs))
        return factors

    def _makeenvconfig(self, name, section, subs, config):
        vc = VenvConfig(envname=name)
        vc.config = config
        factors = set(name.split('-'))
        reader = IniReader(self._cfg, fallbacksections=["testenv"],
            factors=factors)
        reader.addsubstitutions(**subs)
        vc.develop = not config.option.installpkg and \
               reader.getbool(section, "usedevelop", config.option.develop)
        vc.envdir = reader.getpath(section, "envdir", "{toxworkdir}/%s" % name)
        vc.args_are_paths = reader.getbool(section, "args_are_paths", True)
        if reader.getdefault(section, "python", None):
            raise tox.exception.ConfigError(
                "'python=' key was renamed to 'basepython='")
        bp = next((default_factors[f] for f in factors if f in default_factors),
            sys.executable)
        vc.basepython = reader.getdefault(section, "basepython", bp)
        vc._basepython_info = config.interpreters.get_info(vc.basepython)
        reader.addsubstitutions(envdir=vc.envdir, envname=vc.envname,
                                envbindir=vc.envbindir, envpython=vc.envpython,
                                envsitepackagesdir=vc.envsitepackagesdir)
        vc.envtmpdir = reader.getpath(section, "tmpdir", "{envdir}/tmp")
        vc.envlogdir = reader.getpath(section, "envlogdir", "{envdir}/log")
        reader.addsubstitutions(envlogdir=vc.envlogdir, envtmpdir=vc.envtmpdir)
        vc.changedir = reader.getpath(section, "changedir", "{toxinidir}")
        if config.option.recreate:
            vc.recreate = True
        else:
            vc.recreate = reader.getbool(section, "recreate", False)
        args = config.option.args
        if args:
            if vc.args_are_paths:
                args = []
                for arg in config.option.args:
                    origpath = config.invocationcwd.join(arg, abs=True)
                    if origpath.check():
                        arg = vc.changedir.bestrelpath(origpath)
                    args.append(arg)
            reader.addsubstitutions(args)
        setenv = {}
        if config.hashseed is not None:
            setenv['PYTHONHASHSEED'] = config.hashseed
        setenv.update(reader.getdict(section, 'setenv'))
        vc.setenv = setenv
        if not vc.setenv:
            vc.setenv = None

        vc.commands = reader.getargvlist(section, "commands")
        vc.whitelist_externals = reader.getlist(section,
                                                "whitelist_externals")
        vc.deps = []
        for depline in reader.getlist(section, "deps"):
            m = re.match(r":(\w+):\s*(\S+)", depline)
            if m:
                iname, name = m.groups()
                ixserver = config.indexserver[iname]
            else:
                name = depline.strip()
                ixserver = None
            name = self._replace_forced_dep(name, config)
            vc.deps.append(DepConfig(name, ixserver))
        vc.distribute = reader.getbool(section, "distribute", False)
        vc.sitepackages = self.config.option.sitepackages or \
                          reader.getbool(section, "sitepackages", False)

        vc.downloadcache = None
        downloadcache = reader.getdefault(section, "downloadcache")
        if downloadcache:
            # env var, if present, takes precedence
            downloadcache = os.environ.get("PIP_DOWNLOAD_CACHE", downloadcache)
            vc.downloadcache = py.path.local(downloadcache)

        pip_default_opts = ["--pre", "{opts}", "{packages}"]
        vc.install_command = reader.getargv(
            section,
            "install_command",
            "pip install " + " ".join(pip_default_opts),
            )
        if '{packages}' not in vc.install_command:
            raise tox.exception.ConfigError(
             "'install_command' must contain '{packages}' substitution")
        return vc

    def _getenvdata(self, reader, toxsection):
        envstr = self.config.option.env                                \
            or os.environ.get("TOXENV")                                \
            or reader.getdefault(toxsection, "envlist", replace=False) \
            or []
        envlist = _split_env(envstr)

        # collect section envs
        all_envs = set(envlist) - set(["ALL"])
        for section in self._cfg:
            if section.name.startswith(testenvprefix):
                all_envs.add(section.name[len(testenvprefix):])
        if not all_envs:
            all_envs.add("python")

        if not envlist or "ALL" in envlist:
            envlist = sorted(all_envs)

        return envlist, all_envs

    def _replace_forced_dep(self, name, config):
        """
        Override the given dependency config name taking --force-dep-version
        option into account.

        :param name: dep config, for example ["pkg==1.0", "other==2.0"].
        :param config: Config instance
        :return: the new dependency that should be used for virtual environments
        """
        if not config.option.force_dep:
            return name
        for forced_dep in config.option.force_dep:
            if self._is_same_dep(forced_dep, name):
                return forced_dep
        return name

    @classmethod
    def _is_same_dep(cls, dep1, dep2):
        """
        Returns True if both dependency definitions refer to the
        same package, even if versions differ.
        """
        dep1_name = pkg_resources.Requirement.parse(dep1).project_name
        dep2_name = pkg_resources.Requirement.parse(dep2).project_name
        return dep1_name == dep2_name


def _split_env(env):
    """if handed a list, action="append" was used for -e """
    if not isinstance(env, list):
        env = [env]
    return mapcat(_expand_envstr, env)

def _split_factor_expr(expr):
    partial_envs = _expand_envstr(expr)
    return [set(e.split('-')) for e in partial_envs]

def _expand_envstr(envstr):
    # split by commas not in groups
    tokens = re.split(r'(\{[^}]+\})|,', envstr)
    envlist = [''.join(g).strip()
               for k, g in itertools.groupby(tokens, key=bool) if k]

    def expand(env):
        tokens = re.split(r'\{([^}]+)\}', env)
        parts = [token.split(',') for token in tokens]
        return [''.join(variant) for variant in itertools.product(*parts)]

    return mapcat(expand, envlist)

def mapcat(f, seq):
    return list(itertools.chain.from_iterable(map(f, seq)))

class DepConfig:
    def __init__(self, name, indexserver=None):
        self.name = name
        self.indexserver = indexserver

    def __str__(self):
        if self.indexserver:
            if self.indexserver.name == "default":
               return self.name
            return ":%s:%s" %(self.indexserver.name, self.name)
        return str(self.name)
    __repr__ = __str__

class IndexServerConfig:
    def __init__(self, name, url=None):
        self.name = name
        self.url = url

RE_ITEM_REF = re.compile(
    r'''
    (?<!\\)[{]
    (?:(?P<sub_type>[^[:{}]+):)?    # optional sub_type for special rules
    (?P<substitution_value>[^{}]*)  # substitution key
    [}]
    ''',
    re.VERBOSE)


class IniReader:
    def __init__(self, cfgparser, fallbacksections=None, factors=()):
        self._cfg = cfgparser
        self.fallbacksections = fallbacksections or []
        self.factors = factors
        self._subs = {}
        self._subststack = []

    def addsubstitutions(self, _posargs=None, **kw):
        self._subs.update(kw)
        if _posargs:
            self.posargs = _posargs

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

    def getdict(self, section, name, sep="\n"):
        s = self.getdefault(section, name, None)
        if s is None:
            return {}

        value = {}
        for line in s.split(sep):
            if not line.strip():
                continue
            name, rest = line.split('=', 1)
            value[name.strip()] = rest.strip()

        return value

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
        posargs = getattr(self, "posargs", None)

        # Iterate through each word of the command substituting as
        # appropriate to construct the new command string. This
        # string is then broken up into exec argv components using
        # shlex.
        newcommand = ""
        for word in CommandParser(command).words():
            if word == "{posargs}" or word == "[]":
                if posargs:
                    newcommand += " ".join(posargs)
                continue
            elif word.startswith("{posargs:") and word.endswith("}"):
                if posargs:
                    newcommand += " ".join(posargs)
                    continue
                else:
                    word = word[9:-1]
            new_arg = ""
            new_word = self._replace(word)
            new_word = self._replace(new_word)
            new_arg += new_word
            newcommand += new_arg

        # Construct shlex object that will not escape any values,
        # use all values as is in argv.
        shlexer = shlex.shlex(newcommand, posix=True)
        shlexer.whitespace_split = True
        shlexer.escape = ''
        shlexer.commenters = ''
        argv = list(shlexer)
        return argv

    def getargv(self, section, name, default=None, replace=True):
        command = self.getdefault(
            section, name, default=default, replace=False)
        return self._processcommand(command.strip())

    def getbool(self, section, name, default=None):
        s = self.getdefault(section, name, default)
        if not s:
            s = default
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
        x = None
        for s in [section] + self.fallbacksections:
            try:
                x = self._cfg[s][name]
                break
            except KeyError:
                continue

        if x is None:
            x = default
        else:
            x = self._apply_factors(x)

        if replace and x and hasattr(x, 'replace'):
            self._subststack.append((section, name))
            try:
                x = self._replace(x)
            finally:
                assert self._subststack.pop() == (section, name)
        #print "getdefault", section, name, "returned", repr(x)
        return x

    def _apply_factors(self, s):
        def factor_line(line):
            m = re.search(r'^([\w{}\.,-]+)\:\s+(.+)', line)
            if not m:
                return line

            expr, line = m.groups()
            if any(fs <= self.factors for fs in _split_factor_expr(expr)):
                return line

        lines = s.strip().splitlines()
        return '\n'.join(filter(None, map(factor_line, lines)))

    def _replace_env(self, match):
        match_value = match.group('substitution_value')
        if not match_value:
            raise tox.exception.ConfigError(
                'env: requires an environment variable name')

        default = None
        envkey_split = match_value.split(':', 1)

        if len(envkey_split) is 2:
            envkey, default = envkey_split
        else:
            envkey = match_value

        if not envkey in os.environ and default is None:
            raise tox.exception.ConfigError(
                "substitution env:%r: unkown environment variable %r" %
                (envkey, envkey))

        return os.environ.get(envkey, default)

    def _substitute_from_other_section(self, key):
        if key.startswith("[") and "]" in key:
            i = key.find("]")
            section, item = key[1:i], key[i+1:]
            if section in self._cfg and item in self._cfg[section]:
                if (section, item) in self._subststack:
                    raise ValueError('%s already in %s' %(
                            (section, item), self._subststack))
                x = str(self._cfg[section][item])
                self._subststack.append((section, item))
                try:
                    return self._replace(x)
                finally:
                    self._subststack.pop()

        raise tox.exception.ConfigError(
            "substitution key %r not found" % key)

    def _replace_substitution(self, match):
        sub_key = match.group('substitution_value')
        val = self._subs.get(sub_key, None)
        if val is None:
            val = self._substitute_from_other_section(sub_key)
        if py.builtin.callable(val):
            val = val()
        return str(val)

    def _replace_match(self, match):
        g = match.groupdict()

        # special case: opts and packages. Leave {opts} and
        # {packages} intact, they are replaced manually in
        # _venv.VirtualEnv.run_install_command.
        sub_value = g['substitution_value']
        if sub_value in ('opts', 'packages'):
            return '{%s}' % sub_value

        handlers = {
            'env' : self._replace_env,
            None : self._replace_substitution,
            }
        try:
            sub_type = g['sub_type']
        except KeyError:
            raise tox.exception.ConfigError("Malformed substitution; no substitution type provided")

        try:
            handler = handlers[sub_type]
        except KeyError:
            raise tox.exception.ConfigError("No support for the %s substitution type" % sub_type)

        return handler(match)

    def _replace(self, x):
        if '{' in x:
            return RE_ITEM_REF.sub(self._replace_match, x)
        return x

    def _parse_command(self, command):
        pass

class CommandParser(object):

    class State(object):
        def __init__(self):
            self.word = ''
            self.depth = 0
            self.yield_words = []

    def __init__(self, command):
        self.command = command

    def words(self):
        ps = CommandParser.State()

        def word_has_ended():
            return ((cur_char in string.whitespace and ps.word and
               ps.word[-1] not in string.whitespace) or
              (cur_char == '{' and ps.depth == 0 and not ps.word.endswith('\\')) or
              (ps.depth == 0 and ps.word and ps.word[-1] == '}') or
              (cur_char not in string.whitespace and ps.word and
               ps.word.strip() == ''))

        def yield_this_word():
            yieldword = ps.word
            ps.word = ''
            if yieldword:
                ps.yield_words.append(yieldword)

        def yield_if_word_ended():
            if word_has_ended():
                yield_this_word()

        def accumulate():
            ps.word += cur_char

        def push_substitution():
            ps.depth += 1

        def pop_substitution():
            ps.depth -= 1

        for cur_char in self.command:
            if cur_char in string.whitespace:
                if ps.depth == 0:
                    yield_if_word_ended()
                accumulate()
            elif cur_char == '{':
                yield_if_word_ended()
                accumulate()
                push_substitution()
            elif cur_char == '}':
                accumulate()
                pop_substitution()
            else:
                yield_if_word_ended()
                accumulate()

        if ps.word.strip():
            yield_this_word()
        return ps.yield_words

def getcontextname():
    if 'HUDSON_URL' in os.environ:
        return 'jenkins'
    return None

