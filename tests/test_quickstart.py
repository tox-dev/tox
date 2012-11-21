import tox._quickstart

class TestToxQuickstart(object):
    def test_pytest(self, tmpdir):
        d = {
            'envlist': 'py24, py25, py26, py27, py32, py33, pypy',
            'commands': 'py.test',
            'deps': 'pytest',
        }
        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py24, py25, py26, py27, py32, py33, pypy

[testenv]
commands = py.test
deps = pytest
""".lstrip()
        tox._quickstart.generate(d)
        result = open('tox.ini').read()
        # print(result)
        assert(result == expected_tox_ini)

    def test_setup_py_test(self, tmpdir):
        d = {
            'envlist': 'py26, py27',
            'commands': 'python setup.py test',
            'deps': '',
        }
        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py26, py27

[testenv]
commands = python setup.py test
deps = 
""".lstrip()
        tox._quickstart.generate(d)
        result = open('tox.ini').read()
        # print(result)
        assert(result == expected_tox_ini)

    def test_trial(self, tmpdir):
        d = {
            'envlist': 'py27',
            'commands': 'trial',
            'deps': 'Twisted',
        }
        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py27

[testenv]
commands = trial
deps = Twisted
""".lstrip()
        tox._quickstart.generate(d)
        result = open('tox.ini').read()
        # print(result)
        assert(result == expected_tox_ini)

    def test_nosetests(self, tmpdir):
        d = {
            'envlist': 'py27, py32, py33, pypy',
            'commands': 'nosetests -v',
            'deps': 'nose',
        }
        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py27, py32, py33, pypy

[testenv]
commands = nosetests -v
deps = nose
""".lstrip()
        tox._quickstart.generate(d)
        result = open('tox.ini').read()
        # print(result)
        assert(result == expected_tox_ini)
