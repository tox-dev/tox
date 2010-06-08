import tox
import py

pytest_plugins = "pytester"

from tox._cmdline import Session, parseini

class TestSession:
    def test_make_sdist(self, initproj):
        initproj("example123-0.5", filedefs={
            'tests': {'test_hello.py': "def test_hello(): pass"},
            'tox.ini': '''
            '''
        })
        config = parseini("tox.ini")
        session = Session(config)
        sdist = session.get_fresh_sdist()
        assert sdist.check()
        assert sdist == config.toxdir.join("dist", sdist.basename)
        sdist2 = session.get_fresh_sdist()
        assert sdist2 == sdist 
        sdist.write("hello")
        assert sdist.stat().size < 10
        sdist_new = Session(config).get_fresh_sdist()
        assert sdist_new == sdist
        assert sdist_new.stat().size > 10

    def test_log_pcall(self, initproj, tmpdir, capfd):
        initproj("logexample123-0.5", filedefs={
            'tests': {'test_hello.py': "def test_hello(): pass"},
            'tox.ini': '''
            '''
        })
        config = parseini("tox.ini")
        session = Session(config)
        assert not session.config.logdir.listdir()
        opts = {}
        capfd.readouterr()
        session.report.popen(["ls", ], log=None, opts=opts)
        out, err = capfd.readouterr()
        assert '0.log' in out 
        assert 'stdout' in opts
        assert opts['stdout'].write
        assert opts['stderr'] == py.std.subprocess.STDOUT
        x = opts['stdout'].name
        assert x.startswith(str(session.config.logdir))

        opts={}
        session.report.popen(["ls", ], log=None, opts=opts)
        out, err = capfd.readouterr()
        assert '1.log' in out 

        opts={}
        newlogdir = tmpdir.mkdir("newlogdir")
        cwd = newlogdir.dirpath()
        cwd.chdir()
        session.report.popen(["xyz",], log=newlogdir, opts=opts)
        l = newlogdir.listdir()
        assert len(l) == 1
        assert l[0].basename == "0.log"
        out, err = capfd.readouterr()
        relpath = l[0].relto(cwd)
        expect = ">%s/0.log" % (newlogdir.basename)
        assert expect in out

def test_help(cmd):
    result = cmd.run("tox", "-h")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*help*",
    ])

def test_version(cmd):
    result = cmd.run("tox", "--version")
    assert not result.ret
    stdout = result.stdout.str()
    assert tox.__version__ in stdout
    assert "imported from" in stdout

def test_unkonwn_ini(cmd):
    result = cmd.run("tox", "test")
    assert result.ret
    result.stderr.fnmatch_lines([
        "*tox.ini*does not exist*",
    ])

def test_config_specific_ini(tmpdir, cmd):
    ini = tmpdir.ensure("hello.ini")
    result = cmd.run("tox", "-c", ini, "config")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*config-file*hello.ini*",
    ])

# not sure we want this option ATM
def XXX_test_package(cmd, initproj):
    initproj("myproj-0.6", filedefs={
        'tests': {'test_hello.py': "def test_hello(): pass"},
        'MANIFEST.in': """
            include doc
            include myproj
            """,
        'tox.ini': ''
    })
    result = cmd.run("tox", "package")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*created sdist package at*",
    ])

def test_test_simple(cmd, initproj):
    initproj("example123-0.5", filedefs={
        'tests': {'test_hello.py': """
            def test_hello(pytestconfig):
                pytestconfig.mktemp("hello")
            """,
        },
        'tox.ini': '''
            [test]
            changedir=tests 
            command=py.test --basetemp=%(envtmpdir)s --junitxml=junit-%(envname)s.xml 
            deps=py
        '''
    })
    result = cmd.run("tox", "test")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*junit-python.xml*",
        "*1 passed*",
    ])
    result = cmd.run("tox", "test", "--env=python", )
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*1 passed*",
    ])

def test_test_piphelp(initproj, cmd):
    initproj("example123", filedefs={'tox.ini': """
        # content of: tox.ini
        [test]
        command=pip -h
        [testenv:py25]
        python=python2.5
        [testenv:py26]
        python=python2.6
    """})
    result = cmd.run("tox", "test")
    assert not result.ret
