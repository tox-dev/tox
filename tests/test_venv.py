import py
import tox
import os, sys
from tox._venv import VirtualEnv, CreationConfig, getdigest

#def test_global_virtualenv(capfd):
#    v = VirtualEnv()
#    l = v.list()
#    assert l
#    out, err = capfd.readouterr()
#    assert not out
#    assert not err
#
def test_getdigest(tmpdir):
    assert getdigest(tmpdir) == "0"*32

def test_find_executable():
    from tox._venv import find_executable
    p = find_executable(sys.executable)
    assert p == py.path.local(sys.executable)
    for ver in [""] + "2.4 2.5 2.6 2.7 3.1".split():
        name = "python%s" % ver
        if sys.platform == "win32":
            pydir = "python%s" % ver.replace(".", "")
            x = py.path.local("c:\%s" % pydir)
            print (x)
            if not x.check():
                continue
        else:
            if not py.path.local.sysfind(name):
                continue
        p = find_executable(name)
        assert p
        popen = py.std.subprocess.Popen([str(p), '-V'],
                stderr=py.std.subprocess.PIPE)
        stdout, stderr = popen.communicate()
        assert ver in py.builtin._totext(stderr, "ascii")

def test_getsupportedinterpreter(monkeypatch, newconfig, mocksession):
    config = newconfig([], """
        [testenv:python]
        basepython=%s
    """ % sys.executable)
    venv = VirtualEnv(config.envconfigs['python'], session=mocksession)
    interp = venv.getsupportedinterpreter()
    # realpath needed for debian symlinks
    assert interp == py.path.local(sys.executable).realpath()
    monkeypatch.setattr(sys, 'platform', "win32")
    monkeypatch.setattr(venv.envconfig, 'basepython', 'jython')
    py.test.raises(tox.exception.UnsupportedInterpreter,
                   venv.getsupportedinterpreter)
    monkeypatch.undo()
    monkeypatch.setattr(venv.envconfig, 'basepython', 'notexistingpython')
    py.test.raises(tox.exception.InterpreterNotFound,
                   venv.getsupportedinterpreter)

def test_create(monkeypatch, mocksession, newconfig):
    config = newconfig([], """
        [testenv:py123]
    """)
    envconfig = config.envconfigs['py123']
    venv = VirtualEnv(envconfig, session=mocksession)
    assert venv.path == envconfig.envdir
    assert not venv.path.check()
    venv.create()
    l = mocksession._pcalls
    assert len(l) >= 1
    args = l[0].args
    assert str(args[1]).endswith("virtualenv.py")
    if sys.platform != "win32":
        # realpath is needed for stuff like the debian symlinks
        assert py.path.local(sys.executable).realpath() == args[0]
        #assert Envconfig.toxworkdir in args
        assert venv.getcommandpath("easy_install")
    interp = venv._getliveconfig().python
    assert interp == venv.getconfigexecutable()
    assert venv.path_config.check(exists=False)

def test_create_distribute(monkeypatch, mocksession, newconfig):
    config = newconfig([], """
        [testenv:py123]
        distribute=False
    """)
    envconfig = config.envconfigs['py123']
    venv = VirtualEnv(envconfig, session=mocksession)
    assert venv.path == envconfig.envdir
    assert not venv.path.check()
    venv.create()
    l = mocksession._pcalls
    assert len(l) >= 1
    args = l[0].args
    assert "--distribute" not in map(str, args)

def test_create_sitepackages(monkeypatch, mocksession, newconfig):
    config = newconfig([], """
        [testenv:site]
        sitepackages=True

        [testenv:nosite]
        sitepackages=False
    """)
    envconfig = config.envconfigs['site']
    venv = VirtualEnv(envconfig, session=mocksession)
    venv.create()
    l = mocksession._pcalls
    assert len(l) >= 1
    args = l[0].args
    assert "--no-site-packages" not in map(str, args)
    mocksession._clearmocks()

    envconfig = config.envconfigs['nosite']
    venv = VirtualEnv(envconfig, session=mocksession)
    venv.create()
    l = mocksession._pcalls
    assert len(l) >= 1
    args = l[0].args
    assert "--no-site-packages" in map(str, args)

def test_install_deps_wildcard(newmocksession):
    mocksession = newmocksession([], """
        [testenv:py123]
        deps=
            {distshare}/dep1-*
    """)
    venv = mocksession.getenv("py123")
    venv.create()
    l = mocksession._pcalls
    assert len(l) == 1
    distshare = venv.session.config.distshare
    distshare.ensure("dep1-1.0.zip")
    distshare.ensure("dep1-1.1.zip")

    venv.install_deps()
    assert len(l) == 2
    args = l[1].args
    assert l[1].cwd == venv.envconfig.envlogdir
    assert "pip" in str(args[0])
    assert args[1] == "install"
    arg = "--download-cache=" + str(venv.envconfig.downloadcache)
    assert arg in args[2:]
    args = [arg for arg in args if str(arg).endswith("dep1-1.1.zip")]
    assert len(args) == 1


def test_install_downloadcache(newmocksession):
    mocksession = newmocksession([], """
        [testenv:py123]
        distribute=True
        deps=
            dep1
            dep2
    """)
    venv = mocksession.getenv("py123")
    venv.create()
    l = mocksession._pcalls
    assert len(l) == 1

    venv.install_deps()
    assert len(l) == 2
    args = l[1].args
    assert l[1].cwd == venv.envconfig.envlogdir
    assert "pip" in str(args[0])
    assert args[1] == "install"
    arg = "--download-cache=" + str(venv.envconfig.downloadcache)
    assert arg in args[2:]
    assert "dep1" in args
    assert "dep2" in args
    deps = filter(None, [x[1] for x in venv._getliveconfig().deps])
    assert deps == ['dep1', 'dep2']

def test_install_deps_indexserver(newmocksession):
    mocksession = newmocksession([], """
        [tox]
        indexserver =
            abc = ABC
        [testenv:py123]
        deps=
            dep1
            :abc:dep2
    """)
    venv = mocksession.getenv('py123')
    venv.create()
    l = mocksession._pcalls
    assert len(l) == 1
    l[:] = []

    venv.install_deps()
    # two different index servers, two calls
    assert len(l) == 2
    args = " ".join(l[0].args)
    assert "-i" not in args
    assert "dep1" in args

    args = " ".join(l[1].args)
    assert "-i ABC" in args
    assert "dep2" in args

def test_install_sdist_indexserver(newmocksession, tmpdir):
    mocksession = newmocksession([], """
        [tox]
        indexserver =
            default = ABC
    """)
    venv = mocksession.getenv('python')
    l = mocksession._pcalls
    p = tmpdir.ensure("distfile.tar.gz")
    venv.install_sdist(str(p))
    # two different index servers, two calls
    assert len(l) == 1
    args = " ".join(l[0].args)
    assert "-i ABC" in args

def test_install_recreate(newmocksession):
    mocksession = newmocksession(['--recreate'], """
        [testenv]
        deps=xyz
    """)
    venv = mocksession.getenv('python')
    venv.update()
    venv.install_sdist("xz")
    mocksession.report.expect("action", "*creating virtualenv*")
    venv.update()
    mocksession.report.expect("action", "recreating virtualenv*")

def test_install_error(newmocksession, monkeypatch):
    mocksession = newmocksession(['--recreate'], """
        [testenv]
        deps=xyz
        commands=
            qwelkqw
    """)
    venv = mocksession.getenv('python')
    venv.test()
    mocksession.report.expect("error", "*not find*qwelkqw*")

def test_install_command_not_installed(newmocksession, monkeypatch):
    mocksession = newmocksession(['--recreate'], """
        [testenv]
        commands=
            py.test
    """)
    venv = mocksession.getenv('python')
    venv.test()
    mocksession.report.expect("warning", "*test command found but not*")

def test_install_python3(tmpdir, newmocksession):
    if not py.path.local.sysfind('python3.1'):
        py.test.skip("needs python3.1")
    mocksession = newmocksession([], """
        [testenv:py123]
        basepython=python3.1
        deps=
            dep1
            dep2
    """)
    venv = mocksession.getenv('py123')
    venv.create()
    l = mocksession._pcalls
    assert len(l) == 1
    args = l[0].args
    assert str(args[1]).endswith('virtualenv.py')
    l[:] = []
    venv._install(["hello"])
    assert len(l) == 1
    args = l[0].args
    assert 'pip' in str(args[0])
    for x in args:
        assert "--download-cache" not in args, args

class TestCreationConfig:

    def test_basic(self, newconfig, mocksession, tmpdir):
        config = newconfig([], "")
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        assert cconfig.matches(cconfig)
        path = tmpdir.join("configdump")
        cconfig.writeconfig(path)
        newconfig = CreationConfig.readconfig(path)
        assert newconfig.matches(cconfig)
        assert cconfig.matches(newconfig)

    def test_matchingdependencies(self, newconfig, mocksession):
        config = newconfig([], """
            [testenv]
            deps=abc
        """)
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        config = newconfig([], """
            [testenv]
            deps=xyz
        """)
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        otherconfig = venv._getliveconfig()
        assert not cconfig.matches(otherconfig)

    def test_matchingdependencies_file(self, newconfig, mocksession):
        config = newconfig([], """
            [tox]
            distshare={toxworkdir}/distshare
            [testenv]
            deps=abc
                 {distshare}/xyz.zip
        """)
        xyz = config.distshare.join("xyz.zip")
        xyz.ensure()
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        assert cconfig.matches(cconfig)
        xyz.write("hello")
        newconfig = venv._getliveconfig()
        assert not cconfig.matches(newconfig)

    def test_matchingdependencies_latest(self, newconfig, mocksession):
        config = newconfig([], """
            [tox]
            distshare={toxworkdir}/distshare
            [testenv]
            deps={distshare}/xyz-*
        """)
        xyz = config.distshare.ensure("xyz-1.2.0.zip")
        xyz2 = config.distshare.ensure("xyz-1.2.1.zip")
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        md5, path = cconfig.deps[0]
        assert path == xyz2
        assert md5 == path.computehash()

    def test_python_recreation(self, newconfig, mocksession):
        config = newconfig([], "")
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        cconfig = venv._getliveconfig()
        venv.update()
        assert not venv.path_config.check()
        venv.install_sdist("sdist.zip")
        assert venv.path_config.check()
        assert mocksession._pcalls
        args1 = map(str, mocksession._pcalls[0].args)
        assert 'virtualenv' in " ".join(args1)
        mocksession.report.expect("action", "creating virtualenv*")
        # modify config and check that recreation happens
        mocksession._clearmocks()
        venv.update()
        mocksession.report.expect("action", "reusing existing*")
        mocksession._clearmocks()
        cconfig.python = py.path.local("balla")
        cconfig.writeconfig(venv.path_config)
        venv.update()
        mocksession.report.expect("action", "recreating virtualenv*")

    def test_dep_recreation(self, newconfig, mocksession):
        config = newconfig([], "")
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        venv.update()
        cconfig = venv._getliveconfig()
        cconfig.deps[:] = [("1"*32, "xyz.zip")]
        cconfig.writeconfig(venv.path_config)
        mocksession._clearmocks()
        venv.update()
        mocksession.report.expect("action", "recreating virtualenv*")

    def test_distribute_recreation(self, newconfig, mocksession):
        config = newconfig([], "")
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        venv.update()
        cconfig = venv._getliveconfig()
        cconfig.distribute = False
        cconfig.writeconfig(venv.path_config)
        mocksession._clearmocks()
        venv.update()
        mocksession.report.expect("action", "recreating virtualenv*")

class TestVenvTest:

    def test_patchPATH(self, newmocksession, monkeypatch):
        monkeypatch.setenv("PIP_RESPECT_VIRTUALENV", "1")
        mocksession = newmocksession([], """
            [testenv:python]
            commands=abc
        """)
        venv = mocksession.getenv("python")
        envconfig = venv.envconfig
        monkeypatch.setenv("PATH", "xyz")
        oldpath = venv.patchPATH()
        assert oldpath == "xyz"
        res = os.environ['PATH']
        assert res == "%s%sxyz" % (envconfig.envbindir, os.pathsep)
        p = "xyz"+os.pathsep+str(envconfig.envbindir)
        monkeypatch.setenv("PATH", p)
        venv.patchPATH()
        res = os.environ['PATH']
        assert res == "%s%s%s" %(envconfig.envbindir, os.pathsep, p)

        assert envconfig.commands
        monkeypatch.setattr(venv, '_pcall', lambda *args, **kwargs: 0/0)
        py.test.raises(ZeroDivisionError, "venv._install(list('123'))")
        py.test.raises(ZeroDivisionError, "venv.test()")
        py.test.raises(ZeroDivisionError, "venv.easy_install(['qwe'])")
        py.test.raises(ZeroDivisionError, "venv.pip_install(['qwe'])")
        py.test.raises(ZeroDivisionError, "venv._pcall([1,2,3])")
        monkeypatch.setenv("PIP_RESPECT_VIRTUALENV", "1")
        monkeypatch.setenv("PIP_REQUIRE_VIRTUALENV", "1")
        py.test.raises(ZeroDivisionError, "venv.pip_install(['qwe'])")
        assert 'PIP_RESPECT_VIRTUALENV' not in os.environ
        assert 'PIP_REQUIRE_VIRTUALENV' not in os.environ

def test_setenv_added_to_pcall(mocksession, newconfig):
    config = newconfig([], """
        [testenv:python]
        commands=python -V
        setenv =
            ENV_VAR = value
    """)
    mocksession._clearmocks()

    venv = VirtualEnv(config.envconfigs['python'], session=mocksession)
    # import pdb; pdb.set_trace()
    venv.test()

    l = mocksession._pcalls
    assert len(l) == 1
    args = l[0].args
    env = l[0].env
    assert env is not None
    assert 'ENV_VAR' in env
    assert env['ENV_VAR'] == 'value'

    for e in os.environ:
        assert e in env

def test_install_sdist_no_upgrade(newmocksession):
    mocksession = newmocksession([], "")
    venv = mocksession.getenv('python')
    venv.just_created = True
    venv.envconfig.envdir.ensure(dir=1)
    venv.install_sdist("whatever")
    l = mocksession._pcalls
    assert len(l) == 1
    assert '-U' not in l[0].args

def test_install_sdist_upgrade(newmocksession):
    mocksession = newmocksession([], "")
    venv = mocksession.getenv('python')
    assert not hasattr(venv, 'just_created')
    venv.install_sdist("whatever")
    l = mocksession._pcalls
    assert len(l) == 1
    assert '-U' in l[0].args
    assert '--no-deps' in l[0].args

def test_pip_install(newmocksession):
    mocksession = newmocksession([], "")
    venv = mocksession.getenv('python')
    venv.just_created = True
    venv.envconfig.envdir.ensure(dir=1)
    venv.pip_install(args=["whatever"])
    l = mocksession._pcalls
    assert len(l) == 1
    assert 'pip' in l[0].args[0]
    assert 'install' in l[0].args
    env = l[0].env
    assert env is not None
    assert 'PYTHONIOENCODING' in env
    assert env['PYTHONIOENCODING'] == 'utf_8'
