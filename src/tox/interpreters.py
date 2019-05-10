from __future__ import unicode_literals

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from threading import Lock

import py

import tox
from tox import reporter
from tox.constants import SITE_PACKAGE_QUERY_SCRIPT, VERSION_QUERY_SCRIPT


class Interpreters:
    def __init__(self, hook):
        self.name2executable = {}
        self.executable2info = {}
        self.hook = hook

    def get_executable(self, envconfig):
        """ return path object to the executable for the given
        name (e.g. python2.7, python3.6, python etc.)
        if name is already an existing path, return name.
        If an interpreter cannot be found, return None.
        """
        try:
            return self.name2executable[envconfig.envname]
        except KeyError:
            exe = self.hook.tox_get_python_executable(envconfig=envconfig)
            reporter.verbosity2("{} uses {}".format(envconfig.envname, exe))
            self.name2executable[envconfig.envname] = exe
            return exe

    def get_info(self, envconfig):
        executable = self.get_executable(envconfig)
        name = envconfig.basepython
        if not executable:
            return NoInterpreterInfo(name=name)
        try:
            return self.executable2info[executable]
        except KeyError:
            info = run_and_get_interpreter_info(name, executable)
            self.executable2info[executable] = info
            return info

    def get_sitepackagesdir(self, info, envdir):
        if not info.executable:
            return ""
        envdir = str(envdir)
        try:
            res = exec_on_interpreter(str(info.executable), SITE_PACKAGE_QUERY_SCRIPT, str(envdir))
        except ExecFailed as e:
            reporter.verbosity1("execution failed: {} -- {}".format(e.out, e.err))
            return ""
        else:
            return res["dir"]


def run_and_get_interpreter_info(name, executable):
    assert executable
    try:
        result = exec_on_interpreter(str(executable), VERSION_QUERY_SCRIPT)
        result["version_info"] = tuple(result["version_info"])  # fix json dump transformation
        del result["name"]
        del result["version"]
    except ExecFailed as e:
        return NoInterpreterInfo(name, executable=e.executable, out=e.out, err=e.err)
    else:
        return InterpreterInfo(name, **result)


def exec_on_interpreter(*args):
    from subprocess import Popen, PIPE

    popen = Popen(args, stdout=PIPE, stderr=PIPE, universal_newlines=True)
    out, err = popen.communicate()
    if popen.returncode:
        raise ExecFailed(args[0], args[1:], out, err)
    if err:
        sys.stderr.write(err)
    try:
        result = json.loads(out)
    except Exception:
        raise ExecFailed(args[0], args[1:], out, "could not decode {!r}".format(out))
    return result


class ExecFailed(Exception):
    def __init__(self, executable, source, out, err):
        self.executable = executable
        self.source = source
        self.out = out
        self.err = err


class InterpreterInfo:
    def __init__(self, name, executable, version_info, sysplatform, is_64):
        self.name = name
        self.executable = executable
        self.version_info = version_info
        self.sysplatform = sysplatform
        self.is_64 = is_64

    def __str__(self):
        return "<executable at {}, version_info {}>".format(self.executable, self.version_info)


class NoInterpreterInfo:
    def __init__(self, name, executable=None, out=None, err="not found"):
        self.name = name
        self.executable = executable
        self.version_info = None
        self.out = out
        self.err = err

    def __str__(self):
        if self.executable:
            return "<executable at {}, not runnable>".format(self.executable)
        else:
            return "<executable not found for: {}>".format(self.name)


class PythonSpec(object):
    def __init__(self, name, major, minor, architecture, path):
        self.name = name
        self.major = major
        self.minor = minor
        self.architecture = architecture
        self.path = path

    def __repr__(self):
        msg = "PythonSpec(name={}, major={}, minor={}, architecture={}, path={})"
        return msg.format(self.name, self.major, self.minor, self.architecture, self.path)

    def satisfies(self, req):
        if req.is_abs and self.is_abs and self.path != req.path:
            return False
        if req.name is not None and req.name != self.name:
            return False
        if req.architecture is not None and req.architecture != self.architecture:
            return False
        if req.major is not None and req.major != self.major:
            return False
        if req.minor is not None and req.minor != self.minor:
            return False
        if req.major is None and req.minor is not None:
            return False
        return True

    @property
    def is_abs(self):
        return self.path is not None and os.path.isabs(self.path)

    @classmethod
    def from_name(cls, base_python):
        name, major, minor, architecture, path = None, None, None, None, None
        if os.path.isabs(base_python):
            path = base_python
        else:
            match = re.match(r"(python|pypy|jython)(\d)?(?:\.(\d))?(-(32|64))?", base_python)
            if match:
                groups = match.groups()
                name = groups[0]
                major = int(groups[1]) if len(groups) >= 2 and groups[1] is not None else None
                minor = int(groups[2]) if len(groups) >= 3 and groups[2] is not None else None
                architecture = (
                    int(groups[3]) if len(groups) >= 4 and groups[3] is not None else None
                )
            else:
                path = base_python
        return cls(name, major, minor, architecture, path)


CURRENT = PythonSpec(
    "pypy" if tox.constants.INFO.IS_PYPY else "python",
    sys.version_info[0],
    sys.version_info[1],
    64 if sys.maxsize > 2 ** 32 else 32,
    sys.executable,
)

if not tox.INFO.IS_WIN:

    @tox.hookimpl
    def tox_get_python_executable(envconfig):
        base_python = envconfig.basepython
        spec = PythonSpec.from_name(base_python)
        # first, check current
        if spec.name is not None and CURRENT.satisfies(spec):
            return CURRENT.path
        # second check if the literal base python
        candidates = [base_python]
        # third check if the un-versioned name is good
        if spec.name is not None and spec.name != base_python:
            candidates.append(spec.name)
        return check_with_path(candidates, spec)


else:

    @tox.hookimpl
    def tox_get_python_executable(envconfig):
        base_python = envconfig.basepython
        spec = PythonSpec.from_name(base_python)
        # first, check current
        if spec.name is not None and CURRENT.satisfies(spec):
            return CURRENT.path

        # second check if the py.exe has it (only for non path specs)
        if spec.path is None:
            py_exe = locate_via_py(spec)
            if py_exe is not None:
                return py_exe

        # third check if the literal base python is on PATH
        candidates = [envconfig.basepython]
        # fourth check if the name is on PATH
        if spec.name is not None and spec.name != base_python:
            candidates.append(spec.name)
        # or check known locations
        if spec.major is not None and spec.minor is not None:
            if spec.name == "python":
                # The standard names are in predictable places.
                candidates.append(r"c:\python{}{}\python.exe".format(spec.major, spec.minor))
        return check_with_path(candidates, spec)

    _PY_AVAILABLE = []
    _PY_LOCK = Lock()

    def locate_via_py(spec):
        with _PY_LOCK:
            if not _PY_AVAILABLE:
                _call_py()
                _PY_AVAILABLE.append(CURRENT)
        for cur_spec in _PY_AVAILABLE:
            if cur_spec.satisfies(spec):
                return cur_spec.path

    def _call_py():
        py_exe = py.path.local.sysfind("py")
        if py_exe:
            cmd = [str(py_exe), "-0p"]
            proc = subprocess.Popen(
                cmd, universal_newlines=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE
            )
            out, err = proc.communicate()
            if not proc.returncode:
                elements = [
                    tuple(j.strip() for j in i.split("\t")) for i in out.splitlines() if i.strip()
                ]
                if elements:
                    for ver_arch, exe in elements:
                        _, version, arch = ver_arch.split("-")
                        major, minor = version.split(".")
                        _PY_AVAILABLE.append(
                            PythonSpec("python", int(major), int(minor), int(arch), exe)
                        )
            else:
                reporter.verbosity1(
                    "failed {}, error {},\noutput\n:{}\nstderr:\n{}".format(
                        cmd, proc.returncode, out, err
                    )
                )


def check_with_path(candidates, spec):
    for path in candidates:
        base = path
        if not os.path.isabs(path):
            path = py.path.local.sysfind(path)
            reporter.verbosity2(("path found", path))
        if path is not None:
            if os.path.exists(str(path)):
                cur_spec = exe_spec(path, base)
                if cur_spec is not None and cur_spec.satisfies(spec):
                    return cur_spec.path
            else:
                reporter.verbosity2("no such file {}".format(path))


_SPECS = {}
_SPECK_LOCK = defaultdict(Lock)


def exe_spec(python_exe, base):
    if not isinstance(python_exe, str):
        python_exe = str(python_exe)
    with _SPECK_LOCK[python_exe]:
        if python_exe not in _SPECS:
            info = get_python_info([python_exe])
            if info is not None:
                found = PythonSpec(
                    info["name"],
                    info["version_info"][0],
                    info["version_info"][1],
                    64 if info["is_64"] else 32,
                    info["executable"],
                )
                reporter.verbosity2("{} ({}) is {}".format(base, python_exe, info))
            else:
                found = None
            _SPECS[python_exe] = found
    return _SPECS[python_exe]


def get_python_info(cmd):
    proc = subprocess.Popen(
        cmd + [VERSION_QUERY_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    out, err = proc.communicate()
    if not proc.returncode:
        try:
            result = json.loads(out)
        except ValueError as exception:
            failure = exception
        else:
            return result
    else:
        failure = "exit code {}".format(proc.returncode)
    reporter.verbosity1("{!r} cmd {!r} out {!r} err {!r} ".format(failure, cmd, out, err))
