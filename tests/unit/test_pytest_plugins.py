"""
Test utility tests, intended to cover use-cases not used in the current
project test suite, e.g. as shown by the code coverage report.

"""
import os
import sys

import py.path
import pytest

from tox._pytestplugin import RunResult, _filedefs_contains, _path_parts


class TestInitProj:
    @pytest.mark.parametrize(
        "kwargs", ({}, {"src_root": None}, {"src_root": ""}, {"src_root": "."})
    )
    def test_no_src_root(self, kwargs, tmpdir, initproj):
        initproj("black_knight-42", **kwargs)
        init_file = tmpdir.join("black_knight", "black_knight", "__init__.py")
        expected = b'""" module black_knight """' + linesep_bytes() + b"__version__ = '42'"
        assert init_file.read_binary() == expected

    def test_existing_src_root(self, tmpdir, initproj):
        initproj("spam-666", src_root="ham")
        assert not tmpdir.join("spam", "spam").check(exists=1)
        init_file = tmpdir.join("spam", "ham", "spam", "__init__.py")
        expected = b'""" module spam """' + linesep_bytes() + b"__version__ = '666'"
        assert init_file.read_binary() == expected

    def test_prebuilt_src_dir_with_no_src_root(self, tmpdir, initproj):
        initproj("spam-1.0", filedefs={"spam": {}})
        src_dir = tmpdir.join("spam", "spam")
        assert src_dir.check(dir=1)
        assert not src_dir.join("__init__.py").check(exists=1)

    def test_prebuilt_src_dir_with_src_root(self, tmpdir, initproj):
        initproj(
            "spam-1.0",
            filedefs={"incontinentia": {"spam": {"__init__.py": "buttocks"}}},
            src_root="incontinentia",
        )
        assert not tmpdir.join("spam", "spam").check(exists=1)
        init_file = tmpdir.join("spam", "incontinentia", "spam", "__init__.py")
        assert init_file.read_binary() == b"buttocks"

    def test_broken_py_path_local_join_workaround_on_Windows(self, tmpdir, initproj, monkeypatch):
        # construct an absolute folder path for our src_root folder without the
        # Windows drive indicator
        src_root = tmpdir.join("spam")
        src_root = _path_parts(src_root)
        src_root[0] = ""
        src_root = "/".join(src_root)

        # make sure tmpdir drive is the current one so the constructed src_root
        # folder path gets interpreted correctly on Windows
        monkeypatch.chdir(tmpdir)

        # will throw an assertion error if the bug is not worked around
        initproj("spam-666", src_root=src_root)

        init_file = tmpdir.join("spam", "spam", "__init__.py")
        expected = b'""" module spam """' + linesep_bytes() + b"__version__ = '666'"
        assert init_file.read_binary() == expected


def linesep_bytes():
    return os.linesep.encode()


class TestPathParts:
    @pytest.mark.parametrize(
        "input, expected",
        (
            ("", []),
            ("/", ["/"]),
            ("//", ["//"]),
            ("/a", ["/", "a"]),
            ("/a/", ["/", "a"]),
            ("/a/b", ["/", "a", "b"]),
            ("a", ["a"]),
            ("a/b", ["a", "b"]),
        ),
    )
    def test_path_parts(self, input, expected):
        assert _path_parts(input) == expected

    def test_on_py_path(self):
        cwd_parts = _path_parts(py.path.local())
        folder_parts = _path_parts(py.path.local("a/b/c"))
        assert folder_parts[len(cwd_parts) :] == ["a", "b", "c"]


@pytest.mark.parametrize(
    "base, filedefs, target, expected",
    (
        ("/base", {}, "", False),
        ("/base", {}, "/base", False),
        ("/base", {"a": {"b": "data"}}, "", True),
        ("/base", {"a": {"b": "data"}}, "a", True),
        ("/base", {"a": {"b": "data"}}, "a/b", True),
        ("/base", {"a": {"b": "data"}}, "a/x", False),
        ("/base", {"a": {"b": "data"}}, "a/b/c", False),
        ("/base", {"a": {"b": "data"}}, "/base", True),
        ("/base", {"a": {"b": "data"}}, "/base/a", True),
        ("/base", {"a": {"b": "data"}}, "/base/a/b", True),
        ("/base", {"a": {"b": "data"}}, "/base/a/x", False),
        ("/base", {"a": {"b": "data"}}, "/base/a/b/c", False),
        ("/base", {"a": {"b": "data"}}, "/a", False),
    ),
)
def test_filedefs_contains(base, filedefs, target, expected):
    assert bool(_filedefs_contains(base, filedefs, target)) == expected


def test_run_result_repr(capfd):
    with RunResult(["hello", "world"], capfd) as run_result:
        # simulate tox writing some unicode output
        stdout_buffer = getattr(sys.stdout, "buffer", sys.stdout)
        stdout_buffer.write(u"\u2603".encode("UTF-8"))

    # must not `UnicodeError` on repr(...)
    ret = repr(run_result)
    # must be native `str`, (bytes in py2, str in py3)
    assert isinstance(ret, str)
