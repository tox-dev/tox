import subprocess

import pytest


def need_executable(name, check_cmd):
    def wrapper(fn):
        try:
            subprocess.check_output(check_cmd)
        except OSError:
            return pytest.mark.skip(reason="{} is not available".format(name))(fn)
        return fn

    return wrapper


def need_git(fn):
    return pytest.mark.git(need_executable("git", ("git", "--version"))(fn))
