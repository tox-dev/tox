"""Get information about an interpreter"""
from __future__ import absolute_import, print_function, unicode_literals

import copy
import json
import logging
import os
import platform
import sys
from collections import OrderedDict, namedtuple

IS_WIN = sys.platform == "win32"

VersionInfo = namedtuple("VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"])


class PythonInfo:
    """Contains information for a Python interpreter"""

    def __init__(self):
        # qualifies the python
        self.platform = sys.platform
        self.implementation = platform.python_implementation()

        # this is a tuple in earlier, struct later, unify to our own named tuple
        self.version_info = VersionInfo(*list(sys.version_info))
        self.architecture = 64 if sys.maxsize > 2 ** 32 else 32

        self.executable = sys.executable  # executable we were called with
        self.original_executable = self.executable
        self.base_executable = getattr(
            sys, "_base_executable", None
        )  # some platforms may set this

        self.version = sys.version
        self.os = os.name

        # information about the prefix - determines python home
        self.prefix = getattr(sys, "prefix", None)  # prefix we think
        self.base_prefix = getattr(sys, "base_prefix", None)  # venv
        self.real_prefix = getattr(sys, "real_prefix", None)  # old virtualenv

        # information about the exec prefix - dynamic stdlib modules
        self.base_exec_prefix = getattr(sys, "base_exec_prefix", None)
        self.exec_prefix = getattr(sys, "exec_prefix", None)

        try:
            __import__("venv")
            has = True
        except ImportError:
            has = False
        self.has_venv = has
        self.path = sys.path

    @property
    def is_old_virtualenv(self):
        return self.real_prefix is not None

    @property
    def is_venv(self):
        return self.base_prefix is not None and self.version_info.major == 3

    def __repr__(self):
        return "PythonInfo({!r})".format(self.__dict__)

    def to_json(self):
        data = copy.deepcopy(self.__dict__)
        # noinspection PyProtectedMember
        data["version_info"] = data["version_info"]._asdict()  # namedtuple to dictionary
        return json.dumps(data)

    @classmethod
    def from_json(cls, payload):
        data = json.loads(payload)
        data["version_info"] = VersionInfo(
            **data["version_info"]
        )  # restore this to a named tuple structure
        info = copy.deepcopy(CURRENT)
        info.__dict__ = data
        return info

    @property
    def system_prefix(self):
        return self.real_prefix or self.base_prefix or self.prefix

    @property
    def system_exec_prefix(self):
        return self.real_prefix or self.base_exec_prefix or self.exec_prefix

    @property
    def system_executable(self):
        env_prefix = self.real_prefix or self.base_prefix
        if env_prefix:
            if self.real_prefix is None and self.base_executable is not None:
                return self.base_executable
            return self.find_exe(env_prefix)
        else:
            return self.executable

    def find_exe(self, home):
        # we don't know explicitly here, do some guess work - our executable name should tell
        exe_base_name = os.path.basename(self.executable)
        name_candidate = OrderedDict()
        name_candidate[exe_base_name] = None
        for ver in range(3, -1, -1):
            version = ".".join(str(i) for i in sys.version_info[0:ver])
            name = "python{}{}".format(version, ".exe" if IS_WIN else "")
            name_candidate[name] = None
        candidate_folder = OrderedDict()
        if self.executable.startswith(self.prefix):
            relative = self.executable[len(self.prefix) : -len(exe_base_name)]
            candidate_folder["{}{}".format(home, relative)] = None
        candidate_folder[home] = None
        for folder in candidate_folder:
            for name in name_candidate:
                candidate = os.path.join(folder, name)
                if os.path.exists(candidate):
                    return candidate
        msg = "failed to detect {} in {}".format(
            "|".join(name_candidate.keys()), "|".join(candidate_folder)
        )
        raise RuntimeError(msg)

    @classmethod
    def from_exe(cls, exe, raise_on_error=True):
        import subprocess
        import os

        path = "{}.py".format(os.path.splitext(__file__)[0])
        cmd = [exe, path]
        try:
            process = subprocess.Popen(
                cmd,
                universal_newlines=True,
                stdin=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
            )
            out, err = process.communicate()
            code = process.returncode
        except subprocess.CalledProcessError as exception:
            out, err, code = exception.stdout, exception.stderr, exception.returncode
        if code != 0:
            if raise_on_error:
                raise RuntimeError(
                    "failed {} with code {} out {} err {}".format(cmd, code, out, err)
                )
            else:
                logging.debug("failed %s with code %s out %s err %s", cmd, code, out, err)
                return None

        result = cls.from_json(out)
        result.executable = exe  # keep original executable as this may contain initialization code
        return result

    def satisfies(self, req, impl_must_match):
        if self.executable == req.path:
            return True
        if req.path is not None and os.path.isabs(req.path):
            return False
        if impl_must_match:
            if req.implementation is not None and req.implementation != self.implementation:
                return False
        if req.architecture is not None and req.architecture != self.architecture:
            return False

        for our, reqs in zip(self.version_info[0:3], (req.major, req.minor, req.patch)):
            if reqs is not None and our is not None and our != reqs:
                return False
        return True


CURRENT = PythonInfo()


if __name__ == "__main__":
    print(CURRENT.to_json())
