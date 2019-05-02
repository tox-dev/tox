from __future__ import unicode_literals

import distutils.util
import json
import re
import subprocess
import sys

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
            reporter.verbosity2("{} detected as {}".format(envconfig.envname, exe))
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
            print("execution failed: {} -- {}".format(e.out, e.err))
            return ""
        else:
            return res["dir"]


def run_and_get_interpreter_info(name, executable):
    assert executable
    try:
        result = exec_on_interpreter(str(executable), VERSION_QUERY_SCRIPT)
        result["version_info"] = tuple(result["version_info"])  # fix json dump transformation
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
    def __init__(self, name, executable, version_info, sysplatform):
        assert executable and version_info
        self.name = name
        self.executable = executable
        self.version_info = version_info
        self.sysplatform = sysplatform

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


if not tox.INFO.IS_WIN:

    @tox.hookimpl
    def tox_get_python_executable(envconfig):
        # first, check current
        py_exe = get_from_current(envconfig)
        if py_exe is not None:
            return py_exe
        # second, check on path
        py_exe = py.path.local.sysfind(envconfig.basepython)
        if py_exe is not None:
            return py_exe
        # third, check if python on path is good
        py_exe = check_python_on_path(version_info(envconfig))
        return py_exe


else:
    # Exceptions to the usual windows mapping
    win32map = {"python": sys.executable, "jython": r"c:\jython2.5.1\jython.bat"}

    @tox.hookimpl
    def tox_get_python_executable(envconfig):
        # first, check current
        py_exe = get_from_current(envconfig)
        if py_exe is not None:
            return py_exe
        # second, check standard location
        version = version_info(envconfig)
        if version:
            # The standard names are in predictable places.
            actual = r"c:\python{}\python.exe".format("".join(str(i) for i in version))
        else:
            actual = win32map.get(envconfig.basepython, None)
        if actual and py.path.local(actual).check():
            return actual

        if version:
            # third, check if the python on path is good
            py_exe = check_python_on_path(version)
            if py_exe is not None:
                return py_exe

            # fifth, use py to determine location - PEP-514 & PEP-397
            py_exe = locate_via_py(*version)
            if py_exe is None:
                return py_exe
        # sixth, try to use sys find
        return py.path.local.sysfind(envconfig.basepython)

    def locate_via_py(*parts):
        py_exe = distutils.spawn.find_executable("py")
        if py_exe:
            ver = "-{}".format(".".join(str(i) for i in parts))
            info = check_version([str(py_exe), ver])
            if info is not None:
                return info["executable"]


def get_from_current(envconfig):
    if (
        envconfig.basepython == "python{}.{}".format(*sys.version_info[0:2])
        or envconfig.basepython == "python{}".format(sys.version_info[0])
        or envconfig.basepython == "python"
    ):
        return sys.executable


def version_info(envconfig):
    match = re.match(r"python(\d)(?:\.(\d))?", envconfig.basepython)
    groups = [int(g) for g in match.groups() if g] if match else []
    return groups


_VALUE = {}


def check_python_on_path(version):
    if "data" not in _VALUE:
        python_exe = py.path.local.sysfind("python")
        found = None
        if python_exe is not None:
            info = check_version([str(python_exe)])
            if info is not None:
                found = info
                reporter.verbosity2("python ({}) is {}".format(python_exe, info))
        _VALUE["data"] = found
    if _VALUE["data"] is not None and _VALUE["data"]["version_info"][0:2] == version:
        return _VALUE["data"]["executable"]


def check_version(cmd):
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
    reporter.info("{!r} cmd {!r} out {!r} err {!r} ".format(failure, cmd, out, err))
