import os
from stat import S_IREAD

from tox.util.path import ensure_empty_dir


def test_remove_read_only(tmpdir):
    nested_dir = tmpdir / "nested_dir"
    nested_dir.mkdir()

    # create read-only file
    read_only_file = nested_dir / "tmpfile.txt"
    with open(str(read_only_file), "w"):
        pass
    os.chmod(str(read_only_file), S_IREAD)

    ensure_empty_dir(nested_dir)

    assert not os.listdir(str(nested_dir))
