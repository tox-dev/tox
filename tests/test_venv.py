import py
import tox
import sys
from tox._venv import VirtualEnv

#def test_global_virtualenv(capfd):
#    v = VirtualEnv()
#    l = v.list()
#    assert l
#    out, err = capfd.readouterr()
#    assert not out
#    assert not err
#

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
    assert interp == sys.executable
    monkeypatch.setattr(sys, 'platform', "win32")
    monkeypatch.setattr(venv.envconfig, 'basepython', 'python3')
    py.test.raises(tox.exception.UnsupportedInterpreter, 
                   venv.getsupportedinterpreter)
    monkeypatch.undo()
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
    assert "virtualenv" in " ".join(args[:2])
    if sys.platform != "win32":
        i = args.index("-p")
        assert i != -1, args
        assert sys.executable == args[i+1]
        #assert Envconfig.toxworkdir in args
        assert venv.getcommandpath("easy_install")
    interp = venv.path_python.read()
    assert interp == venv.getconfigexecutable()

def test_create_distribute(monkeypatch, mocksession, newconfig):
    config = newconfig([], """
        [testenv:py123]
        distribute=True
    """)
    envconfig = config.envconfigs['py123']
    venv = VirtualEnv(envconfig, session=mocksession)
    assert venv.path == envconfig.envdir
    assert not venv.path.check()
    venv.create()
    l = mocksession._pcalls
    assert len(l) >= 1
    args = l[0].args
    assert "--distribute" not in " ".join(args[:2])

@py.test.mark.skipif("sys.version_info[0] >= 3")
def test_install_downloadcache(mocksession, newconfig):
    config = newconfig([], """
        [testenv:py123]
        distribute=True
        deps=
            dep1
            dep2
    """)
    envconfig = config.envconfigs['py123']
    venv = VirtualEnv(envconfig, session=mocksession)
    venv.create()
    l = mocksession._pcalls
    assert len(l) == 1

    venv.install_deps()
    assert len(l) == 2
    args = l[1].args
    assert "pip" in str(args[0])
    assert args[1] == "install"
    arg = "--download-cache=" + str(envconfig.downloadcache)
    assert arg in args[2:]
    assert "dep1" in args
    assert "dep2" in args
    deps = filter(None, venv.path_deps.readlines(cr=0))
    assert deps == ['dep1', 'dep2']

def test_install_python3(tmpdir, mocksession, newconfig):
    if not py.path.local.sysfind('python3.1'):
        py.test.skip("needs python3.1")
    config = newconfig([], """
        [testenv:py123]
        basepython=python3.1
        deps=
            dep1
            dep2
    """)
    envconfig = config.envconfigs['py123']
    venv = VirtualEnv(envconfig, session=mocksession)
    venv.create()
    l = mocksession._pcalls
    assert len(l) == 2
    args = l[0].args
    assert 'virtualenv3' in args[0]
    l[:] = []
    venv._install(["hello"])
    assert len(l) == 1
    args = l[0].args
    assert 'easy_install' in str(args[0])
    for x in args:
        assert "--download-cache" not in args, args

class TestVenvUpdate:

    def test_iscorrectpythonenv(self, newconfig, mocksession):
        config = newconfig([], "")
        envconfig = config.envconfigs['python'] 
        venv = VirtualEnv(envconfig, session=mocksession)
        assert not venv.iscorrectpythonenv()
        ex = venv.getconfigexecutable() 
        assert ex
        venv.path_python.ensure().write(str(ex))
        venv.path_deps.write("")
        assert venv.iscorrectpythonenv()

    def test_matchingdependencies(self, newconfig, mocksession):
        config = newconfig([], """
            [testenv]
            deps=abc
        """)
        envconfig = config.envconfigs['python'] 
        venv = VirtualEnv(envconfig, session=mocksession)
        assert not venv.matchingdependencies()
        venv.path_deps.ensure().write("abc\n")
        assert venv.matchingdependencies()
        venv.path_deps.ensure().write("abc\nxyz\n")
        assert not venv.matchingdependencies()

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
        assert not venv.matchingdependencies()
        venv.path_deps.ensure()
        venv._writedeps(["abc"])
        assert not venv.matchingdependencies()
        venv._writedeps(["abc", xyz])
        assert venv.matchingdependencies()
        xyz.write("hello")
        assert not venv.matchingdependencies()

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
        assert not venv.matchingdependencies()
        venv.path_deps.ensure()
        venv._writedeps([xyz])
        assert not venv.matchingdependencies()
        venv._writedeps([xyz2])
        assert venv.matchingdependencies()

    def test_python_recreation(self, newconfig, mocksession):
        config = newconfig([], "")
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        assert not venv.path_python.check()
        venv.update()
        assert mocksession._pcalls
        args1 = mocksession._pcalls[0].args
        assert 'virtualenv' in " ".join(args1)
        s = venv.path_python.read()
        assert s == sys.executable
        mocksession.report.expect("action", "creating virtualenv*")
        # modify config and check that recreation happens
        venv.path_python.write("hullabulla")
        mocksession._clearmocks()
        venv.update()
        mocksession.report.expect("action", "recreating virtualenv*")

    def test_python_recreate_deps(self, newconfig, mocksession):
        config = newconfig([], """
                [testenv]
                deps=abc123
        """)
        envconfig = config.envconfigs['python']
        venv = VirtualEnv(envconfig, session=mocksession)
        venv.path_python.ensure().write(venv.getconfigexecutable())
        venv.path_deps.write("\n".join(venv.envconfig.deps))
        venv.update()
        assert not mocksession._pcalls
        mocksession.report.expect("action", "reusing existing matching virtualenv*")
        venv.path_deps.write("xyz\n")
        msg = venv.update() 
        mocksession.report.expect("action", "recreating virtualenv*")

class TestVenvTest:

    def test_path_setting(self, newconfig, mocksession):
        config = newconfig([], """
            [testenv]
            commands=
                {envpython} -c pass
        """)
        envconfig = config.envconfigs['python'] 
        venv = VirtualEnv(envconfig, session=mocksession)
        venv.test()
        assert len(mocksession._pcalls) >= 1
        env = mocksession._pcalls[0].env
        path = env['PATH']
        assert path.startswith(str(venv.envconfig.envbindir))
        
