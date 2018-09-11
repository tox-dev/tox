import os

import pytest

import tox
from tox._quickstart import (
    ALTERNATIVE_CONFIG_NAME,
    QUICKSTART_CONF,
    list_modificator,
    main,
    post_process_input,
    prepare_content,
)

ALL_PY_ENVS_AS_STRING = ", ".join(tox.PYTHON.QUICKSTART_PY_ENVS)
ALL_PY_ENVS_WO_LAST_AS_STRING = ", ".join(tox.PYTHON.QUICKSTART_PY_ENVS[:-1])
SIGNS_OF_SANITY = (
    "tox.readthedocs.io",
    "[tox]",
    "[testenv]",
    "envlist = ",
    "deps =",
    "commands =",
)
"""A bunch of elements to be expected in the generated config as marker for basic sanity"""


class _answers:
    """Simulate a series of terminal inputs by popping them from a list if called."""

    def __init__(self, inputs):
        self._inputs = [str(i) for i in inputs]

    def extend(self, items):
        self._inputs.extend(items)

    def __str__(self):
        return "|".join(self._inputs)

    def __call__(self, prompt):
        print("prompt: '{}'".format(prompt))
        try:
            answer = self._inputs.pop(0)
            print("user answer: '{}'".format(answer))
            return answer
        except IndexError:
            pytest.fail("missing user answer for '{}'".format(prompt))


class _cnf:
    """Handle files and args for different test scenarios."""

    SOME_CONTENT = "dontcare"

    def __init__(self, exists=False, names=None, pass_path=False):
        self.original_name = tox.INFO.DEFAULT_CONFIG_NAME
        self.names = names or [ALTERNATIVE_CONFIG_NAME]
        self.exists = exists
        self.pass_path = pass_path

    def __str__(self):
        return self.original_name if not self.exists else str(self.names)

    @property
    def argv(self):
        argv = ["tox-quickstart"]
        if self.pass_path:
            argv.append(os.getcwd())
        return argv

    @property
    def dpath(self):
        return os.getcwd() if self.pass_path else ""

    def create(self):
        paths_to_create = {self._original_path}
        for name in self.names[:-1]:
            paths_to_create.add(os.path.join(self.dpath, name))
        for path in paths_to_create:
            with open(path, "w") as f:
                f.write(self.SOME_CONTENT)

    @property
    def generated_content(self):
        return self._alternative_content if self.exists else self._original_content

    @property
    def already_existing_content(self):
        if not self.exists:
            if os.path.exists(self._alternative_path):
                pytest.fail("alternative path should never exist here")
            pytest.fail("checking for already existing content makes not sense here")
        return self._original_content

    @property
    def path_to_generated(self):
        return os.path.join(os.getcwd(), self.names[-1] if self.exists else self.original_name)

    @property
    def _original_path(self):
        return os.path.join(self.dpath, self.original_name)

    @property
    def _alternative_path(self):
        return os.path.join(self.dpath, self.names[-1])

    @property
    def _original_content(self):
        with open(self._original_path) as f:
            return f.read()

    @property
    def _alternative_content(self):
        with open(self._alternative_path) as f:
            return f.read()


class _exp:
    """Holds test expectations and a user scenario description."""

    STANDARD_EPECTATIONS = [ALL_PY_ENVS_AS_STRING, "pytest", "pytest"]

    def __init__(self, name, exp=None):
        self.name = name
        exp = exp or self.STANDARD_EPECTATIONS
        # NOTE extra mangling here ensures formatting is the same in file and exp
        map_ = {"deps": list_modificator(exp[1]), "commands": list_modificator(exp[2])}
        post_process_input(map_)
        map_["envlist"] = exp[0]
        self.content = prepare_content(QUICKSTART_CONF.format(**map_))

    def __str__(self):
        return self.name


@pytest.mark.usefixtures("work_in_clean_dir")
@pytest.mark.parametrize(
    argnames="answers, exp, cnf",
    ids=lambda param: str(param),
    argvalues=(
        (
            _answers([4, "Y", "Y", "Y", "Y", "Y", "N", "pytest", "pytest"]),
            _exp(
                "choose versions individually and use pytest",
                [ALL_PY_ENVS_WO_LAST_AS_STRING, "pytest", "pytest"],
            ),
            _cnf(),
        ),
        (
            _answers([4, "Y", "Y", "Y", "Y", "Y", "N", "py.test", ""]),
            _exp(
                "choose versions individually and use old fashioned py.test",
                [ALL_PY_ENVS_WO_LAST_AS_STRING, "pytest", "py.test"],
            ),
            _cnf(),
        ),
        (
            _answers([1, "pytest", ""]),
            _exp(
                "choose current release Python and pytest with defaut deps",
                [tox.PYTHON.CURRENT_RELEASE_ENV, "pytest", "pytest"],
            ),
            _cnf(),
        ),
        (
            _answers([1, "pytest -n auto", "pytest-xdist"]),
            _exp(
                "choose current release Python and pytest with xdist and some args",
                [tox.PYTHON.CURRENT_RELEASE_ENV, "pytest, pytest-xdist", "pytest -n auto"],
            ),
            _cnf(),
        ),
        (
            _answers([2, "pytest", ""]),
            _exp(
                "choose py27, current release Python and pytest with defaut deps",
                ["py27, {}".format(tox.PYTHON.CURRENT_RELEASE_ENV), "pytest", "pytest"],
            ),
            _cnf(),
        ),
        (
            _answers([3, "pytest", ""]),
            _exp("choose all supported version and pytest with defaut deps"),
            _cnf(),
        ),
        (
            _answers([4, "Y", "Y", "Y", "Y", "Y", "N", "py.test", ""]),
            _exp(
                "choose versions individually and use old fashioned py.test",
                [ALL_PY_ENVS_WO_LAST_AS_STRING, "pytest", "py.test"],
            ),
            _cnf(),
        ),
        (
            _answers([4, "", "", "", "", "", "", "", ""]),
            _exp("choose no version individually and defaults"),
            _cnf(),
        ),
        (
            _answers([4, "Y", "Y", "Y", "Y", "Y", "N", "python -m unittest discover", ""]),
            _exp(
                "choose versions individually and use nose with default deps",
                [ALL_PY_ENVS_WO_LAST_AS_STRING, "", "python -m unittest discover"],
            ),
            _cnf(),
        ),
        (
            _answers([4, "Y", "Y", "Y", "Y", "Y", "N", "nosetests", "nose"]),
            _exp(
                "choose versions individually and use nose with default deps",
                [ALL_PY_ENVS_WO_LAST_AS_STRING, "nose", "nosetests"],
            ),
            _cnf(),
        ),
        (
            _answers([4, "Y", "Y", "Y", "Y", "Y", "N", "trial", ""]),
            _exp(
                "choose versions individually and use twisted tests with default deps",
                [ALL_PY_ENVS_WO_LAST_AS_STRING, "twisted", "trial"],
            ),
            _cnf(),
        ),
        (
            _answers([4, "", "", "", "", "", "", "", ""]),
            _exp("existing not overridden, generated to alternative with default name"),
            _cnf(exists=True),
        ),
        (
            _answers([4, "", "", "", "", "", "", "", ""]),
            _exp("existing not overridden, generated to alternative with custom name"),
            _cnf(exists=True, names=["some-other.ini"]),
        ),
        (
            _answers([4, "", "", "", "", "", "", "", ""]),
            _exp("existing not override, generated to alternative"),
            _cnf(exists=True, names=["tox.ini", "some-other.ini"]),
        ),
        (
            _answers([4, "", "", "", "", "", "", "", ""]),
            _exp("existing alternatives are not overridden, generated to alternative"),
            _cnf(exists=True, names=["tox.ini", "setup.py", "some-other.ini"]),
        ),
    ),
)
def test_quickstart(answers, cnf, exp, monkeypatch):
    """Test quickstart script using some little helpers.

    :param _answers answers: user interaction simulation
    :param _cnf cnf: helper for args and config file paths and contents
    :param _exp exp: expectation helper
    """
    monkeypatch.setattr("six.moves.input", answers)
    monkeypatch.setattr("sys.argv", cnf.argv)
    if cnf.exists:
        answers.extend(cnf.names)
        cnf.create()
    main()
    print("generated config at {}:\n{}\n".format(cnf.path_to_generated, cnf.generated_content))
    check_basic_sanity(cnf.generated_content, SIGNS_OF_SANITY)
    assert cnf.generated_content == exp.content
    if cnf.exists:
        assert cnf.already_existing_content == cnf.SOME_CONTENT


def check_basic_sanity(content, signs):
    for sign in signs:
        if sign not in content:
            pytest.fail("{} not in\n{}".format(sign, content))
