import re
from pathlib import Path

import pytest

from tox.pytest import MonkeyPatch
from tox.tox_env.python.req_file import ONE_ARG, RequirementsFile


@pytest.mark.parametrize(
    ["req", "key"],
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
        ("--no-index", "--no-index"),
        ("--find-links /my/local/archives", "--find-links /my/local/archives"),
        ("--find-links \\\n/my/local/archives", "--find-links /my/local/archives"),
        ("--find-links http://some.archives.com/archives", "--find-links http://some.archives.com/archives"),
        ("-i a", "-i a"),
        ("--index-url a", "--index-url a"),
        ("--extra-index-url a", "--extra-index-url a"),
        ("-e a", "-e a"),
        ("--editable a", "--editable a"),
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
        (
            "http://w.org/w_P-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl",
            "http://w.org/w_P-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl",
        ),
        ("git+https://git.example.com/MyProject#egg=MyProject", "git+https://git.example.com/MyProject#egg=MyProject"),
        ("git+ssh://git.example.com/MyProject#egg=MyProject", "git+ssh://git.example.com/MyProject#egg=MyProject"),
        (
            "git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709#egg=MyProject",
            "git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709#egg=MyProject",
        ),
    ],
)
def test_requirements_txt(tmp_path: Path, req: str, key: str) -> None:
    req_file = RequirementsFile(req, root=tmp_path)
    assert req == str(req_file)
    expanded = req_file.validate_and_expand()
    if key:
        assert len(expanded) == 1
        assert expanded[0] == key
    else:
        assert expanded == []
    with req_file.with_file() as filename:
        assert filename.read_text() == req


def test_requirements_txt_local_path_file_protocol(tmp_path: Path) -> None:
    (tmp_path / "downloads").mkdir()
    (tmp_path / "downloads" / "numpy-1.9.2-cp34-none-win32.whl").write_text("1")
    raw = "numpy @ file://./downloads/numpy-1.9.2-cp34-none-win32.whl"
    req = RequirementsFile(raw, root=tmp_path)
    assert req.validate_and_expand() == ["numpy@ file://./downloads/numpy-1.9.2-cp34-none-win32.whl"]
    with req.with_file() as filename:
        assert filename.read_text() == raw


def test_requirements_txt_local_path_implicit(tmp_path: Path) -> None:
    (tmp_path / "downloads").mkdir()
    (tmp_path / "downloads" / "numpy-1.9.2-cp34-none-win32.whl").write_text("1")
    raw = "./downloads/numpy-1.9.2-cp34-none-win32.whl"
    req = RequirementsFile(raw, root=tmp_path)
    assert req.validate_and_expand() == [str(tmp_path / raw)]
    with req.with_file() as filename:
        assert filename.read_text() == raw


def test_requirements_env_var_present(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENV_VAR", "beta")
    req = RequirementsFile("${ENV_VAR} >= 1", root=tmp_path)
    assert req.validate_and_expand() == ["beta>=1"]
    with req.with_file() as filename:
        assert filename.read_text() == "${ENV_VAR} >= 1"


def test_requirements_env_var_missing(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ENV_VAR", raising=False)
    req = RequirementsFile("${ENV_VAR}", root=tmp_path)
    assert req.validate_and_expand() == []
    with req.with_file() as filename:
        assert filename.read_text() == "${ENV_VAR}"


@pytest.mark.parametrize("flag", ["-r", "--requirement"])
def test_requirements_txt_transitive(tmp_path: Path, flag: str) -> None:
    other_req = tmp_path / "other-requirements.txt"
    other_req.write_text("magic\nmagical")
    req = RequirementsFile(f"{flag} other-requirements.txt", root=tmp_path)
    assert req.validate_and_expand() == ["magic", "magical"]
    with req.with_file() as filename:
        assert filename.read_text() == f"{flag} other-requirements.txt"


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
def test_bad_line(raw: str) -> None:
    req = RequirementsFile(raw)
    with pytest.raises(ValueError, match=re.escape(raw)):
        req.validate_and_expand()


def test_requirements_file_missing() -> None:
    req = RequirementsFile("-r one two")
    with pytest.raises(ValueError, match="requirement file path '.*one two' does not exist"):
        req.validate_and_expand()


def test_legacy_requirement_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "requirement.txt").write_text("a")
    raw = RequirementsFile("-rrequirement.txt")
    assert raw.validate_and_expand() == ["a"]


def test_legacy_constraint_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "constraint.txt").write_text("b")
    raw = RequirementsFile("-cconstraint.txt")
    assert raw.validate_and_expand() == ["b"]


@pytest.mark.parametrize("flag", ["-c", "--constraint"])
def test_constraint_txt_expanded(tmp_path: Path, flag: str) -> None:
    other_req = tmp_path / "other.txt"
    other_req.write_text("magic\nmagical")
    req = RequirementsFile(f"{flag} other.txt", root=tmp_path)
    assert req.validate_and_expand() == ["magic", "magical"]
    with req.with_file() as filename:
        assert filename.read_text() == f"{flag} other.txt"


@pytest.mark.parametrize("flag", sorted(ONE_ARG - {"-c", "--constraint", "-r", "--requirement"}))
def test_one_arg_expanded(tmp_path: Path, flag: str) -> None:
    req = RequirementsFile(f"{flag}argument", root=tmp_path)
    assert req.validate_and_expand() == [f"{flag} argument"]
    with req.with_file() as filename:
        assert filename.read_text() == f"{flag} argument"


@pytest.mark.parametrize("escape_upfront", [True, False])
def test_req_path_with_space(tmp_path: Path, escape_upfront: bool) -> None:
    req_file = tmp_path / "a b"
    req_file.write_text("c")
    path = f"-r {str(req_file)}"
    if escape_upfront:
        path = f'{path[:-len("a b")]}a\\ b'
    req = RequirementsFile(path)

    # must be escaped within the requirements file
    assert "a\\ b" in str(req)

    # but still unroll during transitive dependencies
    assert req.validate_and_expand() == ["c"]
