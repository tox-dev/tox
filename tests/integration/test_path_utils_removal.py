import os
from stat import S_IREAD
from tempfile import TemporaryDirectory, NamedTemporaryFile

from tox.util.path import ensure_empty_dir

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


def test_remove_read_only(initproj, cmd):
    temp_dir = TemporaryDirectory()
    read_only_file = NamedTemporaryFile(dir=temp_dir.name, delete=False)
    os.chmod(read_only_file.name, S_IREAD)
    
    ensure_empty_dir(temp_dir.name)
    
    assert not os.path.exists(temp_dir.name)
