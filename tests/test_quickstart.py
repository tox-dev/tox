import pytest
import tox._quickstart


@pytest.fixture(autouse=True)
def cleandir(tmpdir):
    tmpdir.chdir()


class TestToxQuickstartMain(object):

    def mock_term_input_return_values(self, return_values):
        for return_val in return_values:
            yield return_val

    def get_mock_term_input(self, return_values):
        generator = self.mock_term_input_return_values(return_values)

        def mock_term_input(prompt):
            try:
                return next(generator)
            except NameError:
                return generator.next()

        return mock_term_input

    def test_quickstart_main_choose_individual_pythons_and_pytest(
            self,
            monkeypatch):
        monkeypatch.setattr(
            tox._quickstart, 'term_input',
            self.get_mock_term_input(
                [
                    '4',         # Python versions: choose one by one
                    'Y',         # py26
                    'Y',         # py27
                    'Y',         # py32
                    'Y',         # py33
                    'Y',         # py34
                    'Y',         # py35
                    'Y',         # pypy
                    'N',         # jython
                    'py.test',   # command to run tests
                    'pytest'     # test dependencies
                ]
            )
        )

        tox._quickstart.main(argv=['tox-quickstart'])

        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py26, py27, py32, py33, py34, py35, pypy

[testenv]
commands = py.test
deps =
    pytest
""".lstrip()
        result = open('tox.ini').read()
        assert(result == expected_tox_ini)

    def test_quickstart_main_choose_individual_pythons_and_nose_adds_deps(
            self,
            monkeypatch):
        monkeypatch.setattr(
            tox._quickstart, 'term_input',
            self.get_mock_term_input(
                [
                    '4',          # Python versions: choose one by one
                    'Y',          # py26
                    'Y',          # py27
                    'Y',          # py32
                    'Y',          # py33
                    'Y',          # py34
                    'Y',          # py35
                    'Y',          # pypy
                    'N',          # jython
                    'nosetests',  # command to run tests
                    ''            # test dependencies
                ]
            )
        )

        tox._quickstart.main(argv=['tox-quickstart'])

        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py26, py27, py32, py33, py34, py35, pypy

[testenv]
commands = nosetests
deps =
    nose
""".lstrip()
        result = open('tox.ini').read()
        assert(result == expected_tox_ini)

    def test_quickstart_main_choose_individual_pythons_and_trial_adds_deps(
            self,
            monkeypatch):
        monkeypatch.setattr(
            tox._quickstart, 'term_input',
            self.get_mock_term_input(
                [
                    '4',          # Python versions: choose one by one
                    'Y',          # py26
                    'Y',          # py27
                    'Y',          # py32
                    'Y',          # py33
                    'Y',          # py34
                    'Y',          # py35
                    'Y',          # pypy
                    'N',          # jython
                    'trial',      # command to run tests
                    ''            # test dependencies
                ]
            )
        )

        tox._quickstart.main(argv=['tox-quickstart'])

        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py26, py27, py32, py33, py34, py35, pypy

[testenv]
commands = trial
deps =
    twisted
""".lstrip()
        result = open('tox.ini').read()
        assert(result == expected_tox_ini)

    def test_quickstart_main_choose_individual_pythons_and_pytest_adds_deps(
            self,
            monkeypatch):
        monkeypatch.setattr(
            tox._quickstart, 'term_input',
            self.get_mock_term_input(
                [
                    '4',          # Python versions: choose one by one
                    'Y',          # py26
                    'Y',          # py27
                    'Y',          # py32
                    'Y',          # py33
                    'Y',          # py34
                    'Y',          # py35
                    'Y',          # pypy
                    'N',          # jython
                    'py.test',    # command to run tests
                    ''            # test dependencies
                ]
            )
        )
        tox._quickstart.main(argv=['tox-quickstart'])

        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py26, py27, py32, py33, py34, py35, pypy

[testenv]
commands = py.test
deps =
    pytest
""".lstrip()
        result = open('tox.ini').read()
        assert(result == expected_tox_ini)

    def test_quickstart_main_choose_py27_and_pytest_adds_deps(
            self,
            monkeypatch):
        monkeypatch.setattr(
            tox._quickstart, 'term_input',
            self.get_mock_term_input(
                [
                    '1',          # py27
                    'py.test',    # command to run tests
                    ''            # test dependencies
                ]
            )
        )

        tox._quickstart.main(argv=['tox-quickstart'])

        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py27

[testenv]
commands = py.test
deps =
    pytest
""".lstrip()
        result = open('tox.ini').read()
        assert(result == expected_tox_ini)

    def test_quickstart_main_choose_py27_and_py33_and_pytest_adds_deps(
            self,
            monkeypatch):
        monkeypatch.setattr(
            tox._quickstart, 'term_input',
            self.get_mock_term_input(
                [
                    '2',          # py27 and py33
                    'py.test',    # command to run tests
                    ''            # test dependencies
                ]
            )
        )

        tox._quickstart.main(argv=['tox-quickstart'])

        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py27, py33

[testenv]
commands = py.test
deps =
    pytest
""".lstrip()
        result = open('tox.ini').read()
        assert(result == expected_tox_ini)

    def test_quickstart_main_choose_all_pythons_and_pytest_adds_deps(
            self,
            monkeypatch):
        monkeypatch.setattr(
            tox._quickstart, 'term_input',
            self.get_mock_term_input(
                [
                    '3',          # all Python versions
                    'py.test',    # command to run tests
                    ''            # test dependencies
                ]
            )
        )

        tox._quickstart.main(argv=['tox-quickstart'])

        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py26, py27, py32, py33, py34, py35, pypy, jython

[testenv]
commands = py.test
deps =
    pytest
""".lstrip()
        result = open('tox.ini').read()
        assert(result == expected_tox_ini)

    def test_quickstart_main_choose_individual_pythons_and_defaults(
            self,
            monkeypatch):
        monkeypatch.setattr(
            tox._quickstart, 'term_input',
            self.get_mock_term_input(
                [
                    '4',  # Python versions: choose one by one
                    '',   # py26
                    '',   # py27
                    '',   # py32
                    '',   # py33
                    '',   # py34
                    '',   # py35
                    '',   # pypy
                    '',   # jython
                    '',   # command to run tests
                    ''    # test dependencies
                ]
            )
        )

        tox._quickstart.main(argv=['tox-quickstart'])

        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py26, py27, py32, py33, py34, py35, pypy, jython

[testenv]
commands = {envpython} setup.py test
deps =

""".lstrip()
        result = open('tox.ini').read()
        assert(result == expected_tox_ini)

    def test_quickstart_main_existing_tox_ini(self, monkeypatch):
        try:
            f = open('tox.ini', 'w')
            f.write('foo bar\n')
        finally:
            f.close()

        monkeypatch.setattr(
            tox._quickstart, 'term_input',
            self.get_mock_term_input(
                [
                    '4',  # Python versions: choose one by one
                    '',   # py26
                    '',   # py27
                    '',   # py32
                    '',   # py33
                    '',   # py34
                    '',   # py35
                    '',   # pypy
                    '',   # jython
                    '',   # command to run tests
                    '',   # test dependencies
                    '',   # tox.ini already exists; overwrite?
                ]
            )
        )

        tox._quickstart.main(argv=['tox-quickstart'])

        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py26, py27, py32, py33, py34, py35, pypy, jython

[testenv]
commands = {envpython} setup.py test
deps =

""".lstrip()
        result = open('tox-generated.ini').read()
        assert(result == expected_tox_ini)


class TestToxQuickstart(object):
    def test_pytest(self):
        d = {
            'py26': True,
            'py27': True,
            'py32': True,
            'py33': True,
            'py34': True,
            'pypy': True,
            'commands': 'py.test',
            'deps': 'pytest',
        }
        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py26, py27, py32, py33, py34, pypy

[testenv]
commands = py.test
deps =
    pytest
""".lstrip()
        d = tox._quickstart.process_input(d)
        tox._quickstart.generate(d)
        result = open('tox.ini').read()
        # print(result)
        assert(result == expected_tox_ini)

    def test_setup_py_test(self):
        d = {
            'py26': True,
            'py27': True,
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
        d = tox._quickstart.process_input(d)
        tox._quickstart.generate(d)
        result = open('tox.ini').read()
        # print(result)
        assert(result == expected_tox_ini)

    def test_trial(self):
        d = {
            'py27': True,
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
deps =
    Twisted
""".lstrip()
        d = tox._quickstart.process_input(d)
        tox._quickstart.generate(d)
        result = open('tox.ini').read()
        # print(result)
        assert(result == expected_tox_ini)

    def test_nosetests(self):
        d = {
            'py27': True,
            'py32': True,
            'py33': True,
            'py34': True,
            'py35': True,
            'pypy': True,
            'commands': 'nosetests -v',
            'deps': 'nose',
        }
        expected_tox_ini = """
# Tox (http://tox.testrun.org/) is a tool for running tests
# in multiple virtualenvs. This configuration file will run the
# test suite on all supported python versions. To use it, "pip install tox"
# and then run "tox" from this directory.

[tox]
envlist = py27, py32, py33, py34, py35, pypy

[testenv]
commands = nosetests -v
deps =
    nose
""".lstrip()
        d = tox._quickstart.process_input(d)
        tox._quickstart.generate(d)
        result = open('tox.ini').read()
        # print(result)
        assert(result == expected_tox_ini)
