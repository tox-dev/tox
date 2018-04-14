import os

import pytest

import tox._quickstart

ALL_PY_ENVS_AS_STRING = ', '.join(tox._quickstart.ALL_PY_ENVS)
ALL_PY_ENVS_WO_LAST_AS_STRING = ', '.join(tox._quickstart.ALL_PY_ENVS[:-1])


class _term_input:
    """Simulate a series of terminal inputs by popping them from a list if called."""
    def __init__(self, inputs):
        self._inputs = [str(i) for i in inputs]

    def extend(self, items):
        self._inputs.extend(items)

    def __str__(self):
        return "|".join(self._inputs)

    def __call__(self, prompt):
        print("prompt: '%s'" % prompt)
        try:
            answer = self._inputs.pop(0)
            print("user answer: '%s'" % answer)
            return answer
        except IndexError:
            pytest.fail("missing user answer for '%s'" % prompt)


class _ini:
    """Handle files and args for different test scenarios."""
    SOME_CONTENT = 'dontcare'

    def __init__(self, exists=False, names=None, pass_path=False):
        self.original_name = tox._quickstart.NAME
        self.names = names or [tox._quickstart.ALTERNATIVE_NAME]
        self.exists = exists
        self.pass_path = pass_path

    def __str__(self):
        return self.original_name if not self.exists else str(self.names)

    @property
    def argv(self):
        argv = ['tox-quickstart']
        if self.pass_path:
            argv.append(os.getcwd())
        return argv

    @property
    def dpath(self):
        return os.getcwd() if self.pass_path else ''

    def create(self):
        paths_to_create = {self.original_path}
        for name in self.names[:-1]:
            paths_to_create.add(os.path.join(self.dpath, name))
        for path in paths_to_create:
            with open(path, 'w') as f:
                f.write(self.SOME_CONTENT)

    @property
    def actual_path(self):
        return os.path.join(os.getcwd(), self.names[-1] if self.exists else self.original_name)

    @property
    def original_path(self):
        return os.path.join(self.dpath, self.original_name)

    @property
    def alternative_path(self):
        return os.path.join(self.dpath, self.names[-1])

    @property
    def original_content(self):
        with open(self.original_path) as f:
            return f.read()

    @property
    def alternative_content(self):
        with open(self.alternative_path) as f:
            return f.read()


class _exp:
    """Holds test expectations and a user scenario description."""
    STANDARD_EPECTATIONS = [ALL_PY_ENVS_AS_STRING, 'pytest', 'pytest']

    def __init__(self, name, exp=None):
        self.name = name
        exp = exp or self.STANDARD_EPECTATIONS
        # NOTE extra mangling here ensures formatting is the same in file and exp
        self.map = {'deps': tox._quickstart.list_modificator(exp[1]),
                    'commands': tox._quickstart.list_modificator(exp[2])}
        tox._quickstart.post_process_input(self.map)
        self.map['envlist'] = exp[0]

    def __str__(self):
        return self.name


@pytest.mark.usefixtures('work_in_clean_dir')
@pytest.mark.parametrize(argnames='term_input, exp, ini', ids=lambda param: str(param), argvalues=(
    (
        _term_input([4, 'Y', 'Y', 'Y', 'Y', 'Y', 'N', 'pytest', 'pytest']),
        _exp('choose versions individually and use pytest',
             [ALL_PY_ENVS_WO_LAST_AS_STRING, 'pytest', 'pytest']),
        _ini(),
    ),
    (
        _term_input([4, 'Y', 'Y', 'Y', 'Y', 'Y', 'N', 'py.test', '']),
        _exp('choose versions individually and use old fashioned py.test',
             [ALL_PY_ENVS_WO_LAST_AS_STRING, 'pytest', 'py.test']),
        _ini(),
    ),
    (
        _term_input([1, 'pytest', '']),
        _exp('choose current release Python and pytest with defaut deps',
             [tox._quickstart.CURRENT_RELEASE_ENV, 'pytest', 'pytest']),
        _ini(),
    ),
    (
        _term_input([1, 'pytest -n auto', 'pytest-xdist']),
        _exp('choose current release Python and pytest with xdist and some args',
             [tox._quickstart.CURRENT_RELEASE_ENV, 'pytest, pytest-xdist', 'pytest -n auto']),
        _ini(),
    ),
    (
        _term_input([2, 'pytest', '']),
        _exp('choose py27, current release Python and pytest with defaut deps',
             ['py27, %s' % tox._quickstart.CURRENT_RELEASE_ENV, 'pytest', 'pytest']),
        _ini(),
    ),
    (
        _term_input([3, 'pytest', '']),
        _exp('choose all supported version and pytest with defaut deps'),
        _ini(),
    ),
    (
        _term_input([4, 'Y', 'Y', 'Y', 'Y', 'Y', 'N', 'py.test', '']),
        _exp('choose versions individually and use old fashioned py.test',
             [ALL_PY_ENVS_WO_LAST_AS_STRING, 'pytest', 'py.test']),
        _ini(),
    ),
    (
        _term_input([4, '', '', '', '', '', '', '', '']),
        _exp('choose no version individually and defaults'),
        _ini(),
    ),
    (
        _term_input([4, 'Y', 'Y', 'Y', 'Y', 'Y', 'N', 'nosetests', '']),
        _exp('choose versions individually and use nose with default deps',
             [ALL_PY_ENVS_WO_LAST_AS_STRING, 'nose', 'nosetests']),
        _ini(),
    ),
    (
        _term_input([4, 'Y', 'Y', 'Y', 'Y', 'Y', 'N', 'nosetests', '']),
        _exp('choose versions individually and use nose with default deps',
             [ALL_PY_ENVS_WO_LAST_AS_STRING, 'nose', 'nosetests']),
        _ini(),
    ),
    (
        _term_input([4, 'Y', 'Y', 'Y', 'Y', 'Y', 'N', 'trial', '']),
        _exp('choose versions individually and use twisted tests with default deps',
             [ALL_PY_ENVS_WO_LAST_AS_STRING, 'twisted', 'trial']),
        _ini(),
    ),
    (
        _term_input([4, '', '', '', '', '', '', '', '']),
        _exp('existing not overriden, generated to alternative with default name'),
        _ini(exists=True),
    ),
    (
        _term_input([4, '', '', '', '', '', '', '', '']),
        _exp('existing not overriden, generated to alternative with custom name'),
        _ini(exists=True, names=['some-other.ini']),
    ),
    (
        _term_input([4, '', '', '', '', '', '', '', '']),
        _exp('existing not override, generated to alternative'),
        _ini(exists=True, names=['tox.ini', 'some-other.ini']),
    ),
    (
        _term_input([4, '', '', '', '', '', '', '', '']),
        _exp('existing alternatives are not overriden, generated to alternative'),
        _ini(exists=True, names=['tox.ini', 'setup.py', 'some-other.ini']),
    ),
))
def test_quickstart(term_input, ini, exp, monkeypatch):
    """Test quickstart script using some little helpers.

    :param _term_input term_input: user interaction simulation
    :param _ini ini: ini file expectation/creation handler
    :param _exp exp: expectation handler
    """
    monkeypatch.setattr('six.moves.input', term_input)
    monkeypatch.setattr('sys.argv', ini.argv)
    if ini.exists:
        term_input.extend(ini.names)
        ini.create()
    tox._quickstart.main()
    generated_content = tox._quickstart.QUICKSTART_CONF % exp.map
    print("ini at %s" % ini.actual_path)
    if ini.exists:
        assert ini.original_content == ini.SOME_CONTENT
        assert ini.alternative_content == generated_content
    else:
        assert ini.original_content == generated_content
        assert not os.path.exists(ini.alternative_path)
