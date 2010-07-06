import tox
import py

pytest_plugins = "pytester"

from tox._cmdline import Session
from tox._config import parseconfig

class TestSession:
    def test_make_sdist(self, initproj):
        initproj("example123-0.5", filedefs={
            'tests': {'test_hello.py': "def test_hello(): pass"},
            'tox.ini': '''
            '''
        })
        config = parseconfig([])
        session = Session(config)
        sdist = session.sdist()
        assert sdist.check()
        assert sdist.ext == ".zip"
        assert sdist == config.toxdistdir.join(sdist.basename)
        sdist2 = session.sdist()
        assert sdist2 == sdist 
        sdist.write("hello")
        assert sdist.stat().size < 10
        sdist_new = Session(config).sdist()
        assert sdist_new == sdist
        assert sdist_new.stat().size > 10

    def test_make_sdist_distshare(self, tmpdir, initproj):
        distshare = tmpdir.join("distshare")
        initproj("example123-0.6", filedefs={
            'tests': {'test_hello.py': "def test_hello(): pass"},
            'tox.ini': '''
            [tox]
            distshare=%s
            ''' % distshare
        })
        config = parseconfig([])
        session = Session(config)
        sdist = session.sdist()
        assert sdist.check()
        assert sdist.ext == ".zip"
        assert sdist == config.toxdistdir.join(sdist.basename)
        sdist_share = config.distshare.join(sdist.basename)
        assert sdist_share.check()
        assert sdist_share.read("rb") == sdist.read("rb"), (sdist_share, sdist)

    def test_log_pcall(self, initproj, tmpdir, capfd):
        initproj("logexample123-0.5", filedefs={
            'tests': {'test_hello.py': "def test_hello(): pass"},
            'tox.ini': '''
            '''
        })
        config = parseconfig([])
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
        expect = ">%s%s0.log" % (newlogdir.basename, newlogdir.sep)
        assert expect in out

    def test_summary_status(self, initproj, capfd):
        initproj("logexample123-0.5", filedefs={
            'tests': {'test_hello.py': "def test_hello(): pass"},
            'tox.ini': '''
            [testenv:hello]
            [testenv:world]
            '''
        })
        config = parseconfig([])
        session = Session(config)
        envlist = ['hello', 'world']
        envs = session.venvlist
        assert len(envs) == 2
        env1, env2 = envs
        session.setenvstatus(env1, "FAIL XYZ")
        assert session.venvstatus[env1.path]
        session.setenvstatus(env2, 0)
        assert not session.venvstatus[env2.path]
        session._summary()
        out, err = capfd.readouterr()
        exp = "%s: FAIL XYZ" % env1.envconfig.envname 
        assert exp in out
        exp = "%s: commands succeeded" % env2.envconfig.envname 
        assert exp in out
        

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

def test_unknown_interpreter(cmd, initproj):
    initproj("interp123-0.5", filedefs={
        'tests': {'test_hello.py': "def test_hello(): pass"},
        'tox.ini': '''
            [testenv:python]
            basepython=xyz_unknown_interpreter 
            [testenv]
            changedir=tests 
        '''
    })
    result = cmd.run("tox")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*ERROR*InterpreterNotFound*xyz_unknown_interpreter*",
    ])

def test_unknown_dep(cmd, initproj):
    initproj("dep123-0.7", filedefs={
        'tests': {'test_hello.py': "def test_hello(): pass"},
        'tox.ini': '''
            [testenv]
            deps=qweqwe123
            changedir=tests 
        '''
    })
    result = cmd.run("tox", )
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*ERROR*could not install*qweqwe123*",
    ])

def test_unknown_environment(cmd, initproj):
    initproj("env123-0.7", filedefs={
        'tox.ini': ''
    })
    result = cmd.run("tox", "-e", "qpwoei")
    assert result.ret
    result.stdout.fnmatch_lines([
        "*ERROR*unknown*environment*qpwoei*",
    ])

def test_sdist_fails(cmd, initproj):
    initproj("pkg123-0.7", filedefs={
        'tests': {'test_hello.py': "def test_hello(): pass"},
        'setup.py': """
            syntax error
        """
        ,
        'tox.ini': '',
    })
    result = cmd.run("tox", )
    assert result.ret
    result.stdout.fnmatch_lines([
        "*FAIL*could not package project*",
    ])

def test_package_install_fails(cmd, initproj):
    initproj("pkg123-0.7", filedefs={
        'tests': {'test_hello.py': "def test_hello(): pass"},
        'setup.py': """
            from setuptools import setup
            setup(
                name='pkg123',
                description='pkg123 project',
                version='0.7',
                license='GPLv2 or later',
                platforms=['unix', 'win32'],
                packages=['pkg123',],
                install_requires=['qweqwe123'],
                )
            """
        ,
        'tox.ini': '',
    })
    result = cmd.run("tox", )
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*FAIL*could not install package*",
    ])

def test_test_simple(cmd, initproj):
    initproj("example123-0.5", filedefs={
        'tests': {'test_hello.py': """
            def test_hello(pytestconfig):
                pytestconfig.mktemp("hello")
            """,
        },
        'tox.ini': '''
            [testenv]
            changedir=tests 
            commands=
                py.test --basetemp={envtmpdir} --junitxml=junit-{envname}.xml [] 
            deps=py
        '''
    })
    result = cmd.run("tox")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*junit-python.xml*",
        "*1 passed*",
    ])
    result = cmd.run("tox", "-epython", )
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*1 passed*",
        "*summary*",
        "*python: commands succeeded"
    ])
    # see that things work with a different CWD 
    cmd.tmpdir.chdir()
    result = cmd.run("tox", "-c", "example123/tox.ini")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*1 passed*",
        "*summary*",
        "*python: commands succeeded"
    ])
    

def test_test_piphelp(initproj, cmd):
    initproj("example123", filedefs={'tox.ini': """
        # content of: tox.ini
        [testenv]
        commands=pip -h
        [testenv:py25]
        basepython=python2.5
        [testenv:py26]
        basepython=python2.6
    """})
    result = cmd.run("tox")
    assert not result.ret

def test_notest(initproj, cmd):
    initproj("example123", filedefs={'tox.ini': """
        # content of: tox.ini
        [testenv:py25]
        basepython=python2.5
        [testenv:py26]
        basepython=python2.6
    """})
    result = cmd.run("tox", "--notest")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*skipping*test*",
        "*skipping*test*",
        "*tox summary*",
    ])
    result = cmd.run("tox", "--notest", "-epy25")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*reusing*py25",
    ])
    result = cmd.run("tox", "--notest", "-epy25,py26")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*reusing*py25",
        "*reusing*py26",
    ])

def test_sdistonly(initproj, cmd):
    initproj("example123", filedefs={'tox.ini': """
    """})
    result = cmd.run("tox", "--sdistonly")
    assert not result.ret
    assert "setup.py sdist" in result.stdout.str()
    assert "virtualenv" not in result.stdout.str()

def test_separate_sdist_no_sdistfile(cmd, initproj):
    distshare = cmd.tmpdir.join("distshare")
    initproj("pkg123-0.7", filedefs={
        'tox.ini': """
            [tox]
            distshare=%s
        """ % distshare
    })
    result = cmd.run("tox", "--sdistonly")
    assert not result.ret
    l = distshare.listdir()
    assert len(l) == 1
    sdistfile = l[0]

def test_separate_sdist(cmd, initproj):
    distshare = cmd.tmpdir.join("distshare")
    initproj("pkg123-0.7", filedefs={
        'tox.ini': """
            [tox]
            distshare=%s
            sdistsrc={distshare}/pkg123-0.7.zip
        """ % distshare
    })
    result = cmd.run("tox", "--sdistonly")
    assert not result.ret
    l = distshare.listdir()
    assert len(l) == 1
    sdistfile = l[0]
    result = cmd.run("tox", "--notest")
    assert not result.ret 
    result.stdout.fnmatch_lines([
        "*skipping*sdist*",
        "*install*%s*" % sdistfile.basename,
    ])

def test_sdist_latest(tmpdir, newconfig):
    distshare = tmpdir.join("distshare")
    config = newconfig([], """
            [tox]
            distshare=%s
            sdistsrc={distshare}/pkg123-**LATEST**
    """ % distshare)
    distshare.ensure("pkg123-1.3.5.zip")
    p = distshare.ensure("pkg123-1.4.5.zip")
    distshare.ensure("pkg123-1.4.5a1.zip")
    session = Session(config)
    sdist_path = session.sdist()
    assert sdist_path == p
