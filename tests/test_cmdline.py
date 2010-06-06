import tox
import py

pytest_plugins = "pytester"

def test_help(cmd):
    result = cmd.run("tox", "-h")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*help*",
    ])

def test_version(cmd):
    result = cmd.run("tox", "--version")
    assert not result.ret
    assert tox.__version__ in result.stdout.str()

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

@py.test.mark.xfail
def test_package_sdist(cmd, initproj):
    initproj("example123-0.5", filedefs={
        'tests': {'test_hello.py': "def test_hello(): pass"},
        'tox.ini': '''
            [package]
            method=sdist
        '''
    })
    result = cmd.run("tox", "package")
    assert not result.ret
    result.stdout.fnmatch_lines([
        "*created package*example123-0.5*",
    ])

def test_test_simple(cmd, initproj):
    initproj("example123-0.5", filedefs={
        'tests': {'test_hello.py': "def test_hello(): pass"},
        'tox.ini': '''
            [project]
            distpaths = 
                example123
                setup.py
            testpaths = 
                tests 
            [test]
            command=py.test --junitxml=junit-%(envname)s.xml tests
            deps=py
        '''
    })
    result = cmd.run("tox", "test")
    assert not result.ret
    result.stdout.fnmatch_lines([
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
        [project]
        distpaths=
            example123
            setup.py
        [test]
        command=pip -h
        [testenv:py25]
        python=python2.5
        [testenv:py26]
        python=python2.6
    """})
    result = cmd.run("tox", "test")
    assert not result.ret
