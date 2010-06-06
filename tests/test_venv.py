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

def test_find_executable():
    from tox._venv import find_executable
    p = find_executable(sys.executable)
    assert p == py.path.local(sys.executable)
    for ver in [""] + "2.4 2.5 2.6 2.7 3.1".split():
        name = "python%s" % ver
        if sys.platform == "win32":
            pydir = "python%s" % ver.replace(".", "")
            x = py.path.local("c:\%s" % pydir)
            print x
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
        assert ver in stderr

def test_create(tmpdir, monkeypatch):
    class Envconfig:
        envbasedir = tmpdir.ensure("basedir", dir=1)
        envdir = envbasedir.join("envbasedir", "xyz123")
        python = "python"
    l = []
    class MyProj:
        def pcall(self, args, out, cwd):
            l.append(args)
    venv = VirtualEnv(Envconfig, project=MyProj())
    assert venv.path == Envconfig.envdir
    assert not venv.path.check()
    venv.create()
    assert len(l) == 1
    args = l[0]
    assert "virtualenv" in " ".join(args[:2])
    if sys.platform != "win32":
        i = args.index("-p")
        assert i != -1, args
        assert sys.executable == args[i+1]
        #assert Envconfig.envbasedir in args
        assert venv.getcommandpath("easy_install")

@py.test.mark.skipif("sys.version_info[0] >= 3")
def test_install_downloadcache(tmpdir):
    class Envconfig:
        downloadcache = tmpdir.ensure("download", dir=1)
        envbasedir = tmpdir.ensure("basedir", dir=1)
        envdir = envbasedir.join("envbasedir", "xyz123")
        python = sys.executable
    l = []
    class MyProj:
        def pcall(self, args, out, cwd):
            l.append(args)
        
    venv = VirtualEnv(Envconfig, project=MyProj())
    venv.create()
    assert len(l) == 1

    venv.install(["hello", "world"])
    assert len(l) == 2
    args = l[1]
    assert "pip" in str(args[0])
    assert args[1] == "install"
    arg = "--download-cache=" + str(Envconfig.downloadcache)
    assert arg in args[2:]
    assert "hello" in args
    assert "world" in args

def test_install_python3(tmpdir):
    if not py.path.local.sysfind('python3.1'):
        py.test.skip("needs python3.1")
    class Envconfig:
        downloadcache = tmpdir.ensure("download", dir=1)
        envbasedir = tmpdir.ensure("basedir", dir=1)
        envdir = envbasedir.join("envbasedir", "xyz123")
        python = "python3.1"
    l = []
    class MyProj:
        def pcall(self, args, out, cwd):
            l.append(args)
    venv = VirtualEnv(Envconfig, project=MyProj())
    venv.create()
    assert len(l) == 2
    args = l[0]
    assert 'virtualenv3' in args[0]
    l[:] = []
    venv.install(["hello"])
    assert len(l) == 1
    args = l[0]
    assert 'easy_install' in str(args[0])
    for x in args:
        assert "--download-cache" not in args, args
