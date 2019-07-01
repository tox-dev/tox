from __future__ import absolute_import, unicode_literals

import os
from contextlib import contextmanager


@contextmanager
def set_os_env_var(env_var_name, value):
    """Set an environment variable with unrolling once the context exists"""
    prev_value = os.environ.get(env_var_name)
    try:
        os.environ[env_var_name] = str(value)
        yield
    finally:
        if prev_value is None:
            del os.environ[env_var_name]
        else:
            os.environ[env_var_name] = prev_value


def env_diff(env):
    """Diff the given env against the input env"""
    add, rm, change = [], [], []
    if env is not None and env is not os.environ:
        add = [(i, env[i]) for i in sorted(set(env.keys()) - set(os.environ.keys()))]
        rm = [(i, os.environ[i]) for i in sorted(set(os.environ.keys()) - set(env.keys()))]
        change = [
            (i, os.environ[i], env[i])
            for i in sorted(set(env.keys()) & set(os.environ.keys()))
            if env[i] != os.environ[i]
        ]
    return add, rm, change
