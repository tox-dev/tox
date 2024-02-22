from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from io import BytesIO
from typing import IO, TYPE_CHECKING, Any, Iterator

import pytest

from tox.tox_env.python.pip.req.file import ParsedRequirement, RequirementsFile

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from tox.pytest import CaptureFixture, MonkeyPatch

_REQ_FILE_TEST_CASES = [
    pytest.param("--pre", {"pre": True}, [], ["--pre"], id="pre"),
    pytest.param("--no-index", {"index_url": []}, [], ["--no-index"], id="no-index"),
    pytest.param("--no-index\n-i a\n--no-index", {"index_url": []}, [], ["--no-index"], id="no-index overwrites index"),
    pytest.param("--prefer-binary", {"prefer_binary": True}, [], ["--prefer-binary"], id="prefer-binary"),
    pytest.param("--require-hashes", {"require_hashes": True}, [], ["--require-hashes"], id="requires-hashes"),
    pytest.param("--pre ", {"pre": True}, [], ["--pre"], id="space after"),
    pytest.param(" --pre", {"pre": True}, [], ["--pre"], id="space before"),
    pytest.param("--pre\\\n", {"pre": True}, [], ["--pre"], id="newline after"),
    pytest.param("--pre # magic", {"pre": True}, [], ["--pre"], id="comment after space"),
    pytest.param("--pre\t# magic", {"pre": True}, [], ["--pre"], id="comment after tab"),
    pytest.param(
        "--find-links /my/local/archives",
        {"find_links": ["/my/local/archives"]},
        [],
        ["-f", "/my/local/archives"],
        id="find-links path",
    ),
    pytest.param(
        "--find-links /my/local/archives --find-links /my/local/archives",
        {"find_links": ["/my/local/archives"]},
        [],
        ["-f", "/my/local/archives"],
        id="find-links duplicate same line",
    ),
    pytest.param(
        "--find-links /my/local/archives\n--find-links /my/local/archives",
        {"find_links": ["/my/local/archives"]},
        [],
        ["-f", "/my/local/archives"],
        id="find-links duplicate different line",
    ),
    pytest.param(
        "--find-links \\\n/my/local/archives",
        {"find_links": ["/my/local/archives"]},
        [],
        ["-f", "/my/local/archives"],
        id="find-links newline path",
    ),
    pytest.param(
        "--find-links http://some.archives.com/archives",
        {"find_links": ["http://some.archives.com/archives"]},
        [],
        ["-f", "http://some.archives.com/archives"],
        id="find-links url",
    ),
    pytest.param(
        "--index-url a --find-links http://some.archives.com/archives",
        {
            "index_url": ["a"],
            "find_links": ["http://some.archives.com/archives"],
        },
        [],
        ["-i", "a", "-f", "http://some.archives.com/archives"],
        id="index and find",
    ),
    pytest.param("-i a", {"index_url": ["a"]}, [], ["-i", "a"], id="index url short"),
    pytest.param("--index-url a", {"index_url": ["a"]}, [], ["-i", "a"], id="index url long"),
    pytest.param("-i a -i b\n-i c", {"index_url": ["c"]}, [], ["-i", "c"], id="index url multiple"),
    pytest.param(
        "--extra-index-url a",
        {"index_url": ["https://pypi.org/simple", "a"]},
        [],
        ["--extra-index-url", "a"],
        id="extra-index-url",
    ),
    pytest.param(
        "--extra-index-url a --extra-index-url a",
        {"index_url": ["https://pypi.org/simple", "a"]},
        [],
        ["--extra-index-url", "a"],
        id="extra-index-url dup same line",
    ),
    pytest.param(
        "--extra-index-url a\n--extra-index-url a",
        {"index_url": ["https://pypi.org/simple", "a"]},
        [],
        ["--extra-index-url", "a"],
        id="extra-index-url dup different line",
    ),
    pytest.param("-e a", {}, ["-e a"], ["-e", "a"], id="e"),
    pytest.param("--editable a", {}, ["-e a"], ["-e", "a"], id="editable"),
    pytest.param("--editable .[2,1]", {}, ["-e .[1,2]"], ["-e", ".[1,2]"], id="editable extra"),
    pytest.param(".[\t, a1. , B2-\t, C3_, ]", {}, [".[B2-,C3_,a1.]"], [".[B2-,C3_,a1.]"], id="path with extra"),
    pytest.param(".[a.1]", {}, [f".{os.sep}.[a.1]"], [f".{os.sep}.[a.1]"], id="path with invalid extra is path"),
    pytest.param("-f a", {"find_links": ["a"]}, [], ["-f", "a"], id="f"),
    pytest.param("--find-links a", {"find_links": ["a"]}, [], ["-f", "a"], id="find-links"),
    pytest.param("--trusted-host a", {"trusted_hosts": ["a"]}, [], ["--trusted-host", "a"], id="trusted-host"),
    pytest.param(
        "--trusted-host a --trusted-host a",
        {"trusted_hosts": ["a"]},
        [],
        ["--trusted-host", "a"],
        id="trusted-host dup same line",
    ),
    pytest.param(
        "--trusted-host a\n--trusted-host a",
        {"trusted_hosts": ["a"]},
        [],
        ["--trusted-host", "a"],
        id="trusted-host dup different line",
    ),
    pytest.param(
        "--use-feature 2020-resolver",
        {"features_enabled": ["2020-resolver"]},
        [],
        ["--use-feature", "2020-resolver"],
        id="use-feature space",
    ),
    pytest.param(
        "--use-feature=fast-deps",
        {"features_enabled": ["fast-deps"]},
        [],
        ["--use-feature", "fast-deps"],
        id="use-feature equal",
    ),
    pytest.param(
        "--use-feature=fast-deps --use-feature 2020-resolver",
        {"features_enabled": ["2020-resolver", "fast-deps"]},
        [],
        ["--use-feature", "2020-resolver", "--use-feature", "fast-deps"],
        id="use-feature multiple same line",
    ),
    pytest.param(
        "--use-feature=fast-deps\n--use-feature 2020-resolver",
        {"features_enabled": ["2020-resolver", "fast-deps"]},
        [],
        ["--use-feature", "2020-resolver", "--use-feature", "fast-deps"],
        id="use-feature multiple different line",
    ),
    pytest.param(
        "--use-feature=fast-deps\n--use-feature 2020-resolver\n" * 2,
        {"features_enabled": ["2020-resolver", "fast-deps"]},
        [],
        ["--use-feature", "2020-resolver", "--use-feature", "fast-deps"],
        id="use-feature multiple duplicate different line",
    ),
    pytest.param("--no-binary :all:", {"no_binary": {":all:"}}, [], ["--no-binary", {":all:"}], id="no-binary all"),
    pytest.param("--no-binary :none:", {"no_binary": {":none:"}}, [], [], id="no-binary none"),
    pytest.param(
        "--only-binary :all:",
        {"only_binary": {":all:"}},
        [],
        ["--only-binary", {":all:"}],
        id="only-binary all",
    ),
    pytest.param(
        "--only-binary :none:",
        {"only_binary": {":none:"}},
        [],
        [],
        id="only-binary none",
    ),
    pytest.param(
        "--no-binary=foo --only-binary=foo",
        {"only_binary": {"foo"}},
        [],
        ["--only-binary", {"foo"}],
        id="no-binary-and-only-binary",
    ),
    pytest.param(
        "--no-binary=foo --no-binary=:none:",
        {},
        [],
        [],
        id="no-binary-none-last",
    ),
    pytest.param(
        "--only-binary=:none: --no-binary=foo",
        {"no_binary": {"foo"}},
        [],
        ["--no-binary", {"foo"}],
        id="no-binary-none-first",
    ),
    pytest.param(
        "--only-binary foo; sys_platform == 'aix'",
        {"only_binary": {"foo;"}},
        [],
        ["--only-binary", {"foo;"}],
        id="only-binary-and-env-marker",
    ),
    pytest.param("####### example-requirements.txt #######", {}, [], [], id="comment"),
    pytest.param("\t##### Requirements without Version Specifiers ######", {}, [], [], id="tab and comment"),
    pytest.param("  # start", {}, [], [], id="space and comment"),
    pytest.param("nose", {}, ["nose"], ["nose"], id="req"),
    pytest.param("nose\nnose", {}, ["nose"], ["nose"], id="req dup"),
    pytest.param(
        "numpy[2,1]  @ file://./downloads/numpy-1.9.2-cp34-none-win32.whl",
        {},
        ["numpy[1,2]@ file://./downloads/numpy-1.9.2-cp34-none-win32.whl"],
        ["numpy[1,2]@ file://./downloads/numpy-1.9.2-cp34-none-win32.whl"],
        id="path with name-extra-protocol",
    ),
    pytest.param(
        "docopt == 0.6.1             # Version Matching. Must be version 0.6.1",
        {},
        ["docopt==0.6.1"],
        ["docopt==0.6.1"],
        id="req equal comment",
    ),
    pytest.param(
        "keyring >= 4.1.1            # Minimum version 4.1.1",
        {},
        ["keyring>=4.1.1"],
        ["keyring>=4.1.1"],
        id="req ge comment",
    ),
    pytest.param(
        "coverage != 3.5             # Version Exclusion. Anything except version 3.5",
        {},
        ["coverage!=3.5"],
        ["coverage!=3.5"],
        id="req ne comment",
    ),
    pytest.param(
        "Mopidy-Dirble ~= 1.1        # Compatible release. Same as >= 1.1, == 1.*",
        {},
        ["Mopidy-Dirble~=1.1"],
        ["Mopidy-Dirble~=1.1"],
        id="req approx comment",
    ),
    pytest.param("b==1.3", {}, ["b==1.3"], ["b==1.3"], id="req eq"),
    pytest.param("c >=1.2,<2.0", {}, ["c<2.0,>=1.2"], ["c<2.0,>=1.2"], id="req ge lt"),
    pytest.param("d[bar,foo]", {}, ["d[bar,foo]"], ["d[bar,foo]"], id="req extras"),
    pytest.param("d[foo, bar]", {}, ["d[bar,foo]"], ["d[bar,foo]"], id="req extras space"),
    pytest.param("d[foo,\tbar]", {}, ["d[bar,foo]"], ["d[bar,foo]"], id="req extras tab"),
    pytest.param("e~=1.4.2", {}, ["e~=1.4.2"], ["e~=1.4.2"], id="req approx"),
    pytest.param(
        "f ==5.4 ; python_version < '2.7'",
        {},
        ['f==5.4; python_version < "2.7"'],
        ['f==5.4; python_version < "2.7"'],
        id="python version filter",
    ),
    pytest.param(
        "g; sys_platform == 'win32'",
        {},
        ['g; sys_platform == "win32"'],
        ['g; sys_platform == "win32"'],
        id="platform filter",
    ),
    pytest.param(
        "http://w.org/w_P-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl",
        {},
        ["http://w.org/w_P-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl"],
        ["http://w.org/w_P-3.0.3.dev1820+49a8884-cp34-none-win_amd64.whl"],
        id="http URI",
    ),
    pytest.param(
        "git+https://git.example.com/MyProject#egg=MyProject",
        {},
        ["git+https://git.example.com/MyProject#egg=MyProject"],
        ["git+https://git.example.com/MyProject#egg=MyProject"],
        id="vcs with https",
    ),
    pytest.param(
        "git+ssh://git.example.com/MyProject#egg=MyProject",
        {},
        ["git+ssh://git.example.com/MyProject#egg=MyProject"],
        ["git+ssh://git.example.com/MyProject#egg=MyProject"],
        id="vcs with ssh",
    ),
    pytest.param(
        "git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709#egg=MyProject",
        {},
        ["git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709#egg=MyProject"],
        ["git+https://git.example.com/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709#egg=MyProject"],
        id="vcs with commit hash pin",
    ),
    pytest.param(
        "attrs --hash sha384:142d9b02f3f4511ccabf6c14bd34d2b0a9ed043a898228b48343cfdf4eb10856ef7ad5e2ff2c528ecae04"
        "912224782ab\t--hash=sha256:af957b369adcd07e5b3c64d2cdb76d6808c5e0b16c35ca41c79c8eee34808152 # ok",
        {},
        [
            "attrs --hash sha256:af957b369adcd07e5b3c64d2cdb76d6808c5e0b16c35ca41c79c8eee34808152 --hash sha384:"
            "142d9b02f3f4511ccabf6c14bd34d2b0a9ed043a898228b48343cfdf4eb10856ef7ad5e2ff2c528ecae04912224782ab",
        ],
        ["attrs"],
        id="hash",
    ),
    pytest.param(
        "attrs --hash=sha256:af957b369adcd07e5b3c64d2cdb76d6808c5e0b16c35ca41c79c8eee34808152\\\n "
        "--hash sha384:142d9b02f3f4511ccabf6c14bd34d2b0a9ed043a898228b48343cfdf4eb10856ef7ad5"
        "e2ff2c528ecae04912224782ab\n",
        {},
        [
            "attrs --hash sha256:af957b369adcd07e5b3c64d2cdb76d6808c5e0b16c35ca41c79c8eee34808152 --hash sha384:"
            "142d9b02f3f4511ccabf6c14bd34d2b0a9ed043a898228b48343cfdf4eb10856ef7ad5e2ff2c528ecae04912224782ab",
        ],
        ["attrs"],
        id="hash with escaped newline",
    ),
    pytest.param(
        "attrs --hash=sha512:7a91e5a3d1a1238525e477385ef5ee6cecdc8f8fcc2a79d1b35a9f57ad15c814"
        "dada670026f41fdd62e5e10b3fd75d6112704a9521c3df105f0b6f3bb11b128a",
        {},
        [
            "attrs --hash sha512:7a91e5a3d1a1238525e477385ef5ee6cecdc8f8fcc2a79d1b35a9f57ad15c814"
            "dada670026f41fdd62e5e10b3fd75d6112704a9521c3df105f0b6f3bb11b128a",
        ],
        ["attrs"],
        id="sha512 hash is supported",
    ),
    pytest.param(
        "\tp @ https://github.com/a/b/c/d.zip ",
        {},
        ["p@ https://github.com/a/b/c/d.zip"],
        ["p@ https://github.com/a/b/c/d.zip"],
        id="whitespace around",
    ),
]


@pytest.mark.parametrize(("req", "opts", "requirements", "as_args"), _REQ_FILE_TEST_CASES)
def test_req_file(tmp_path: Path, req: str, opts: dict[str, Any], requirements: list[str], as_args: list[str]) -> None:
    requirements_txt = tmp_path / "req.txt"
    requirements_txt.write_text(req)
    req_file = RequirementsFile(requirements_txt, constraint=False)
    assert req_file.as_root_args == as_args
    assert str(req_file) == f"-r {requirements_txt}"
    assert vars(req_file.options) == (opts if {":none:"} not in opts.values() else {})
    found = [str(i) for i in req_file.requirements]
    assert found == requirements


def test_requirements_env_var_present(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ENV_VAR", "beta")
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text("${ENV_VAR} >= 1")
    req_file = RequirementsFile(requirements_file, constraint=False)
    assert vars(req_file.options) == {}
    found = [str(i) for i in req_file.requirements]
    assert found == ["beta>=1"]


def test_requirements_env_var_missing(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("ENV_VAR", raising=False)
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text("${ENV_VAR}")
    req_file = RequirementsFile(requirements_file, constraint=False)
    assert vars(req_file.options) == {}
    found = [str(i) for i in req_file.requirements]
    assert found == [f".{os.sep}${{ENV_VAR}}"]


@pytest.mark.parametrize("flag", ["-r", "--requirement"])
def test_requirements_txt_transitive(tmp_path: Path, flag: str) -> None:
    other_req = tmp_path / "other-requirements.txt"
    other_req.write_text("magic\nmagical")
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(f"{flag} other-requirements.txt\n{flag} other-requirements.txt")
    req_file = RequirementsFile(requirements_file, constraint=False)
    assert req_file.as_root_args == ["-r", "other-requirements.txt"]
    assert req_file.as_root_args is req_file.as_root_args  # check it's cached
    assert vars(req_file.options) == {}
    found = [str(i) for i in req_file.requirements]
    assert found == ["magic", "magical"]


@pytest.mark.parametrize(
    ("raw", "error"),
    [
        ("--pre something", "unrecognized arguments: something"),
        ("--missing", "unrecognized arguments: --missing"),
        ("--index-url a b", "unrecognized arguments: b"),
        ("--index-url", "argument -i/--index-url/--pypi-url: expected one argument"),
        ("-k", "unrecognized arguments: -k"),
    ],
)
def test_bad_line(tmp_path: Path, raw: str, capfd: CaptureFixture, error: str) -> None:
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(raw)
    req_file = RequirementsFile(requirements_file, constraint=False)
    with pytest.raises(ValueError, match=f"^{error}$"):
        assert req_file.options
    out, err = capfd.readouterr()
    assert not out
    assert not err


def test_requirements_file_missing(tmp_path: Path) -> None:
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text("-r one.txt")
    req_file = RequirementsFile(requirements_file, constraint=False)
    with pytest.raises(ValueError, match="No such file or directory: .*one.txt"):
        assert req_file.options


@pytest.mark.parametrize("flag", ["-c", "--constraint"])
def test_constraint_txt_expanded(tmp_path: Path, flag: str) -> None:
    other_req = tmp_path / "other.txt"
    other_req.write_text("magic\nmagical\n-i a")
    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(f"{flag} other.txt\n{flag} other.txt")
    req_file = RequirementsFile(requirements_file, constraint=True)
    assert req_file.as_root_args == ["-c", "other.txt"]
    assert vars(req_file.options) == {"index_url": ["a"]}
    found = [str(i) for i in req_file.requirements]
    assert found == ["-c magic", "-c magical"]


@pytest.mark.skipif(sys.platform == "win32", reason=r"on windows the escaped \ is overloaded by path separator")
def test_req_path_with_space_escape(tmp_path: Path) -> None:
    dep_requirements_file = tmp_path / "a b"
    dep_requirements_file.write_text("c")
    path = f"-r {dep_requirements_file!s}"
    path = f'{path[: -len("a b")]}a\\ b'

    requirements_file = tmp_path / "req.txt"
    requirements_file.write_text(path)
    req_file = RequirementsFile(requirements_file, constraint=False)

    assert vars(req_file.options) == {}
    found = [str(i) for i in req_file.requirements]
    assert found == ["c"]


@pytest.mark.parametrize(
    "hash_value",
    [
        "sha256:a",
        "sha256:xxxxxxxxxx123456789012345678901234567890123456789012345678901234",
        "sha512:thisshouldfail8525e477385ef5ee6cecdc8f8fcc2a79d1b35a9f57ad15c814"
        "dada670026f41fdd62e5e10b3fd75d6112704a9521c3df105f0b6f3bb11b128a",
    ],
)
def test_bad_hash(hash_value: str, tmp_path: Path) -> None:
    requirements_txt = tmp_path / "req.txt"
    requirements_txt.write_text(f"attrs --hash {hash_value}")
    req_file = RequirementsFile(requirements_txt, constraint=False)
    with pytest.raises(ValueError, match=f"^argument --hash: {hash_value}$"):
        assert req_file.requirements


@pytest.mark.parametrize("codec", ["utf-8", "utf-16", "utf-32"])
def test_custom_file_encoding(codec: str, tmp_path: Path) -> None:
    requirements_file = tmp_path / "r.txt"
    raw = "art".encode(codec)
    requirements_file.write_bytes(raw)
    req_file = RequirementsFile(requirements_file, constraint=False)
    assert [str(i) for i in req_file.requirements] == ["art"]


def test_parsed_requirement_properties(tmp_path: Path) -> None:
    req = ParsedRequirement("a", {"b": 1}, str(tmp_path), 1)
    assert req.options == {"b": 1}
    assert str(req.requirement) == "a"
    assert req.from_file == str(tmp_path)
    assert req.lineno == 1


def test_parsed_requirement_repr_with_opt(tmp_path: Path) -> None:
    req = ParsedRequirement("a", {"b": 1}, str(tmp_path), 1)
    assert repr(req) == "ParsedRequirement(requirement=a, options={'b': 1})"


def test_parsed_requirement_repr_no_opt(tmp_path: Path) -> None:
    assert repr(ParsedRequirement("a", {}, str(tmp_path), 2)) == "ParsedRequirement(requirement=a)"


@pytest.mark.parametrize("flag", ["-r", "--requirement", "-c", "--constraint"])
def test_req_over_http(tmp_path: Path, flag: str, mocker: MockerFixture) -> None:
    is_constraint = flag in {"-c", "--constraint"}
    url_open = mocker.patch("tox.tox_env.python.pip.req.file.urlopen", autospec=True)
    url_open.return_value.__enter__.return_value = BytesIO(b"-i i\na")
    requirements_txt = tmp_path / "req.txt"
    requirements_txt.write_text(f"{flag} https://zopefoundation.github.io/Zope/releases/4.5.5/requirements-full.txt")
    req_file = RequirementsFile(requirements_txt, constraint=is_constraint)
    assert str(req_file) == f"-{'c' if is_constraint else 'r'} {requirements_txt}"
    assert vars(req_file.options) == {"index_url": ["i"]}
    found = [str(i) for i in req_file.requirements]
    assert found == [f"{'-c ' if is_constraint else ''}a"]


def test_req_over_http_has_req(tmp_path: Path, mocker: MockerFixture) -> None:
    @contextmanager
    def enter(url: str) -> Iterator[IO[bytes]]:
        if url == "https://root.org/a.txt":
            yield BytesIO(b"-r b.txt")
        elif url == "https://root.org/b.txt":
            yield BytesIO(b"-i i\na")
        else:  # pragma: no cover
            raise RuntimeError  # pragma: no cover

    mocker.patch("tox.tox_env.python.pip.req.file.urlopen", autospec=True, side_effect=enter)

    requirements_txt = tmp_path / "req.txt"
    requirements_txt.write_text("-r https://root.org/a.txt")
    req_file = RequirementsFile(requirements_txt, constraint=False)

    assert vars(req_file.options) == {"index_url": ["i"]}
    found = [str(i) for i in req_file.requirements]
    assert found == ["a"]


@pytest.mark.parametrize(
    "loc",
    ["file://", "file://localhost"],
)
def test_requirement_via_file_protocol(tmp_path: Path, loc: str) -> None:
    other_req = tmp_path / "other-requirements.txt"
    other_req.write_text("-i i\na")
    requirements_text = tmp_path / "req.txt"
    requirements_text.write_text(f"-r {loc}{'/' if sys.platform == 'win32' else ''}{other_req}")

    req_file = RequirementsFile(requirements_text, constraint=False)

    assert vars(req_file.options) == {"index_url": ["i"]}
    found = [str(i) for i in req_file.requirements]
    assert found == ["a"]


def test_requirement_via_file_protocol_na(tmp_path: Path) -> None:
    other_req = tmp_path / "other-requirements.txt"
    other_req.write_text("-i i\na")
    requirements_text = tmp_path / "req.txt"
    requirements_text.write_text(f"-r file://magic.com{'/' if sys.platform == 'win32' else ''}{other_req}")

    req_file = RequirementsFile(requirements_text, constraint=False)
    pattern = r"non-local file URIs are not supported on this platform: 'file://magic\.com\.*"
    with pytest.raises(ValueError, match=pattern):
        assert req_file.options


def test_requirement_to_path_one_level_up(tmp_path: Path) -> None:
    other_req = tmp_path / "other.txt"
    other_req.write_text("-e ..")
    req_file = RequirementsFile(other_req, constraint=False)
    result = req_file.requirements
    assert result[0].requirement == str(tmp_path.parent.resolve())
