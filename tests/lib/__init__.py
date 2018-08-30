import subprocess

import pytest


def need_executable(name, check_cmd):
    def wrapper(fn):
        try:
            subprocess.check_output(check_cmd)
        except OSError:
            return pytest.mark.skip(reason="%s is not available" % name)(fn)
        return fn

    return wrapper


def need_git(fn):
    return pytest.mark.mercurial(need_executable("git", ("git", "--version"))(fn))
