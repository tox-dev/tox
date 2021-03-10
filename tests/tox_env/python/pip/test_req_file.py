import re
from pathlib import Path

import pytest
from packaging.requirements import Requirement
from pytest_mock import MockerFixture

from tox.pytest import MonkeyPatch
from tox.tox_env.python.pip.req_file import (
    ONE_ARG,
    ConstraintFile,
    EditablePathReq,
    Flags,
    PathReq,
    PythonDeps,
    RequirementsFile,
    RequirementWithFlags,
    UrlReq,
)


@pytest.mark.parametrize(
    ("req", "key"),
    [
        ("--pre", "--pre"),
        ("--no-index", "--no-index"),
        ("--prefer-binary", "--prefer-binary"),
        ("--require-hashes", "--require-hashes"),
        ("  --pre", "--pre"),
        ("--pre ", "--pre"),
        (" --pre ", "--pre"),
        ("--pre\\\n", "--pre"),
        ("--pre # magic", "--pre"),
        ("--pre\t# magic", "--pre"),
        ("--find-links /my/local/archives", "--find-links /my/local/archives"),
        ("--find-links \\\n/my/local/archives", "--find-links /my/local/archives"),
        ("--find-links http://some.archives.com/archives", "--find-links http://some.archives.com/archives"),
        ("-i a", "-i a"),
        ("--index-url a", "--index-url a"),
        ("--extra-index-url a", "--extra-index-url a"),
        ("-e a", "-e a"),
        ("--editable a", "-e a"),
        ("-f a", "-f a"),
        ("--find-links a", "--find-links a"),
        ("--trusted-host a", "--trusted-host a"),
        ("--use-feature a", "--use-feature a"),
        ("--use-feature=a", "--use-feature a"),
        ("--no-binary a", "--no-binary a"),
        ("--only-binary a", "--only-binary a"),
        ("--only-binary=a", "--only-binary a"),
        ("####### example-requirements.txt #######", ""),
        ("\t##### Requirements without Version Specifiers ######", ""),
        ("  # start", ""),
        ("nose", "nose"),
        ("docopt == 0.6.1             # Version Matching. Must be version 0.6.1", "docopt==0.6.1"),
        ("keyring >= 4.1.1            # Minimum version 4.1.1", "keyring>=4.1.1"),
        ("coverage != 3.5             # Version Exclusion. Anything except version 3.5", "coverage!=3.5"),
        ("Mopidy-Dirble ~= 1.1        # Compatible release. Same as >= 1.1, == 1.*", "Mopidy-Dirble~=1.1"),
        ("b==1.3", "b==1.3"),
        ("c >=1.2,<2.0", "c<2.0,>=1.2"),
        ("d[foo, bar]", "d[bar,foo]"),
        ("d[foo,  bar]", "d[bar,foo]"),
        ("d[bar,foo]", "d[bar,foo]"),
        ("e~=1.4.2", "e~=1.4.2"),
        ("f ==5.4 ; python_version < '2.7'", 'f==5.4; python_version < "2.7"'),
        ("g; sys_platform == 'win32'", 'g; sys_platform == "win32"'),
        pytest.param(
            "http://w.org/w_P-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl",
            "http://w.org/w_P-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl",
            id="http URI",
        ),
        pytest.param(
            "git+https://git.example.com/MyProject#egg=MyProject",
            "git+https://git.example.com/MyProject#egg=MyProject",
            id="vcs with https",
        ),
        pytest.param(
            "git+ssh://git.example.com/MyProject#egg=MyProject",
            "git+ssh://git.example.com/MyProject#egg=MyProject",
            id="vcs with ssh",
        ),
        pytest.param(
            "git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709#egg=MyProject",
            "git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709#egg=MyProject",
            id="vcs with commit hash pin",
        ),
        pytest.param(
            "attrs --hash=sha256:af957b369adcd07e5b3c64d2cdb76d6808c5e0b16c35ca41c79c8eee34808152\t"
            "--hash sha384:142d9b02f3f4511ccabf6c14bd34d2b0a9ed043a898228b48343cfdf4eb10856ef7ad5"
            "e2ff2c528ecae04912224782ab",
            "attrs --hash=sha256:af957b369adcd07e5b3c64d2cdb76d6808c5e0b16c35ca41c79c8eee34808152 "
            "--hash=sha384:142d9b02f3f4511ccabf6c14bd34d2b0a9ed043a898228b48343cfdf4eb10856ef7ad5"
            "e2ff2c528ecae04912224782ab",
            id="hash",
        ),
        pytest.param(
            "attrs --hash=sha256:af957b369adcd07e5b3c64d2cdb76d6808c5e0b16c35ca41c79c8eee34808152\\\n "
            "--hash sha384:142d9b02f3f4511ccabf6c14bd34d2b0a9ed043a898228b48343cfdf4eb10856ef7ad5"
            "e2ff2c528ecae04912224782ab",
            "attrs --hash=sha256:af957b369adcd07e5b3c64d2cdb76d6808c5e0b16c35ca41c79c8eee34808152 "
            "--hash=sha384:142d9b02f3f4511ccabf6c14bd34d2b0a9ed043a898228b48343cfdf4eb10856ef7ad5"
            "e2ff2c528ecae04912224782ab",
            id="hash with escaped newline",
        ),
    ],
)
def test_requirements_txt(tmp_path: Path, req: str, key: str) -> None:
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(req)
    req_file = RequirementsFile(requirements_file, root=tmp_path)
    assert "-r req.txt" == str(req_file)
    expanded = req_file.validate_and_expand()
    if key:
        assert len(expanded) == 1
        assert str(expanded[0]) == key
    else:
        assert expanded == []


def test_requirements_txt_local_path_file_protocol(tmp_path: Path) -> None:
    (tmp_path / "downloads").mkdir()
    (tmp_path / "downloads" / "numpy-1.9.2-cp34-none-win32.whl").write_text("1")

    raw = "numpy @ file://./downloads/numpy-1.9.2-cp34-none-win32.whl"
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(raw)
    req = RequirementsFile(requirements_file, root=tmp_path)
    expanded = [str(i) for i in req.validate_and_expand()]
    expected = [str(Requirement("numpy@ file://./downloads/numpy-1.9.2-cp34-none-win32.whl"))]
    assert expanded == expected


def test_requirements_txt_local_path_implicit(tmp_path: Path) -> None:
    (tmp_path / "downloads").mkdir()
    (tmp_path / "downloads" / "numpy-1.9.2-cp34-none-win32.whl").write_text("1")
    raw = "./downloads/numpy-1.9.2-cp34-none-win32.whl"
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(raw)
    req = RequirementsFile(requirements_file, root=tmp_path)
    assert [str(i.path) for i in req.validate_and_expand()] == [str(tmp_path / raw)]


def test_requirements_env_var_present(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENV_VAR", "beta")
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text("${ENV_VAR} >= 1")
    req = RequirementsFile(requirements_file, root=tmp_path)
    assert [str(i) for i in req.validate_and_expand()] == ["beta>=1"]


def test_requirements_env_var_missing(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ENV_VAR", raising=False)
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text("${ENV_VAR}")
    req = RequirementsFile(requirements_file, root=tmp_path)
    assert req.validate_and_expand() == []


@pytest.mark.parametrize("flag", ["-r", "--requirement"])
def test_requirements_txt_transitive(tmp_path: Path, flag: str) -> None:
    other_req = tmp_path / "other-requirements.txt"
    other_req.write_text("magic\nmagical")
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(f"{flag} other-requirements.txt")
    req = RequirementsFile(requirements_file, root=tmp_path)
    assert req.unroll() == [{"-r other-requirements.txt": ["magic", "magical"]}]


@pytest.mark.parametrize(
    "raw",
    [
        "--pre something",
        "--missing",
        "--index-url a b",
        "--index-url",
        "-k",
        "magic+https://git.example.com/MyProject#egg=MyProject",
    ],
)
def test_bad_line(tmp_path: Path, raw: str) -> None:
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(raw)
    req = RequirementsFile(requirements_file, root=tmp_path)
    with pytest.raises(ValueError, match=re.escape(raw)):
        req.validate_and_expand()


def test_requirements_file_missing(tmp_path: Path) -> None:
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text("-r one.txt")
    req = RequirementsFile(requirements_file, root=tmp_path)
    with pytest.raises(ValueError, match="requirement file path '.*one.txt' does not exist"):
        req.validate_and_expand()


def test_legacy_requirement_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "requirement.txt").write_text("a")
    raw = PythonDeps("-rrequirement.txt")
    assert raw.unroll() == [{"-r requirement.txt": ["a"]}]


def test_legacy_constraint_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "constraint.txt").write_text("b")
    raw = PythonDeps("-cconstraint.txt")
    assert raw.unroll() == [{"-c constraint.txt": ["b"]}]


@pytest.mark.parametrize("flag", ["-c", "--constraint"])
def test_constraint_txt_expanded(tmp_path: Path, flag: str) -> None:
    other_req = tmp_path / "other.txt"
    other_req.write_text("magic\nmagical")
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(f"{flag} other.txt")
    req = RequirementsFile(requirements_file, root=tmp_path)
    assert req.unroll() == [{"-c other.txt": ["magic", "magical"]}]


@pytest.mark.parametrize("flag", sorted(ONE_ARG - {"-c", "--constraint", "-r", "--requirement"}))
def test_one_arg_expanded(tmp_path: Path, flag: str) -> None:
    req = PythonDeps(f"{flag}argument", root=tmp_path)
    if flag == "--editable":
        flag = "-e"
    assert req.unroll() == [f"{flag} argument"]


def test_req_path_with_space(tmp_path: Path) -> None:
    req_file = tmp_path / "a b"
    req_file.write_text("c")
    path = f"-r {str(req_file)}"
    path = f'{path[:-len("a b")]}a\\ b'

    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(path)
    req = RequirementsFile(requirements_file, root=tmp_path)

    # must be escaped within the requirements file
    assert "a\\ b" in req._raw

    # but still unroll during transitive dependencies
    assert req.unroll() == [{"-r a b": ["c"]}]
    assert str(req) == "-r req.txt"


def test_flags() -> None:
    flag = Flags("-i", "a")

    assert flag.as_args() == ("-i", "a")
    assert str(flag) == "-i a"

    assert flag != Flags("-i", "b")
    assert flag == Flags("-i", "a")
    assert flag != object


def test_requirement_with_flags_no_args() -> None:
    req = RequirementWithFlags("a", ())

    assert req.as_args() == ("a",)
    assert str(req) == "a"

    assert req == RequirementWithFlags("a", ())
    assert req != object
    assert req != RequirementWithFlags("b", ())
    assert req != RequirementWithFlags("a", ("b"))


def test_requirement_with_flags_has_args() -> None:
    req = RequirementWithFlags("a", ("1"))

    assert req.as_args() == ("a", "1")
    assert str(req) == "a 1"

    assert req == RequirementWithFlags("a", ("1"))
    assert req != object
    assert req != RequirementWithFlags("a", ())
    assert req != RequirementWithFlags("a", ("2"))


def test_path_req(tmp_path: Path) -> None:
    path_req = PathReq(tmp_path)

    assert path_req.as_args() == (str(tmp_path),)
    assert str(path_req) == str(tmp_path)

    assert path_req != PathReq(tmp_path / "a")
    assert path_req == PathReq(tmp_path)
    assert path_req != object


def test_editable_path_req(tmp_path: Path) -> None:
    editable_path_req = EditablePathReq(tmp_path)

    assert editable_path_req.as_args() == ("-e", str(tmp_path))
    assert str(editable_path_req) == f"-e {tmp_path}"

    assert editable_path_req != EditablePathReq(tmp_path / "a")
    assert editable_path_req == EditablePathReq(tmp_path)
    assert editable_path_req != object


def test_url_req() -> None:
    path_req = UrlReq("a")

    assert path_req.as_args() == ("a",)
    assert str(path_req) == "a"

    assert path_req != UrlReq("b")
    assert path_req == UrlReq("a")
    assert path_req != object


def test_invalid_flag_python_dep(mocker: MockerFixture) -> None:
    mocker.patch("tox.tox_env.python.pip.req_file.ONE_ARG", ONE_ARG | {"--magic"})
    with pytest.raises(ValueError, match="--magic"):
        PythonDeps("--magic a").unroll()


def test_requirement_file_str(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    req_file = tmp_path / "a" / "r.txt"
    req_file.write_text("a")

    assert str(RequirementsFile(req_file, tmp_path)) == f"-r {Path('a') / 'r.txt'}"

    here = Path(__file__).parent
    try:
        tmp_path.relative_to(here)
    except ValueError:
        assert str(RequirementsFile(req_file, here)) == f"-r {req_file}"


def test_requirement_file_eq(tmp_path: Path) -> None:
    req_file = tmp_path / "r.txt"
    req_file.write_text("a")
    assert RequirementsFile(req_file, tmp_path) == RequirementsFile(req_file, tmp_path)

    req_file_2 = tmp_path / "r2.txt"
    req_file_2.write_text("a")

    assert RequirementsFile(req_file, tmp_path) != RequirementsFile(req_file_2, tmp_path)
    assert RequirementsFile(req_file, tmp_path) != ConstraintFile(req_file, tmp_path)


def test_constraint_file_eq(tmp_path: Path) -> None:
    constraint_file = tmp_path / "r.txt"
    constraint_file.write_text("a")
    assert ConstraintFile(constraint_file, tmp_path) == ConstraintFile(constraint_file, tmp_path)

    constraint_file_2 = tmp_path / "r2.txt"
    constraint_file_2.write_text("a")

    assert ConstraintFile(constraint_file, tmp_path) != ConstraintFile(constraint_file_2, tmp_path)
    assert ConstraintFile(constraint_file, tmp_path) != RequirementsFile(constraint_file, tmp_path)
