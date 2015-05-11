import sys
import py
import re
import inspect
from tox import hookimpl


class Interpreters:
    def __init__(self, hook):
        self.name2executable = {}
        self.executable2info = {}
        self.hook = hook

    def get_executable(self, envconfig):
        """ return path object to the executable for the given
        name (e.g. python2.6, python2.7, python etc.)
        if name is already an existing path, return name.
        If an interpreter cannot be found, return None.
        """
        try:
            return self.name2executable[envconfig.envname]
        except KeyError:
            exe = self.hook.tox_get_python_executable(envconfig=envconfig)
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
            res = exec_on_interpreter(info.executable,
                                      [inspect.getsource(sitepackagesdir),
                                       "print (sitepackagesdir(%r))" % envdir])
        except ExecFailed:
            val = sys.exc_info()[1]
            print ("execution failed: %s -- %s" % (val.out, val.err))
            return ""
        else:
            return res["dir"]


def run_and_get_interpreter_info(name, executable):
    assert executable
    try:
        result = exec_on_interpreter(executable,
                                     [inspect.getsource(pyinfo), "print (pyinfo())"])
    except ExecFailed:
        val = sys.exc_info()[1]
        return NoInterpreterInfo(name, executable=val.executable,
                                 out=val.out, err=val.err)
    else:
        return InterpreterInfo(name, executable, **result)


def exec_on_interpreter(executable, source):
    if isinstance(source, list):
        source = "\n".join(source)
    from subprocess import Popen, PIPE
    args = [str(executable)]
    popen = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    popen.stdin.write(source.encode("utf8"))
    out, err = popen.communicate()
    if popen.returncode:
        raise ExecFailed(executable, source, out, err)
    try:
        result = eval(out.strip())
    except Exception:
        raise ExecFailed(executable, source, out,
                         "could not decode %r" % out)
    return result


class ExecFailed(Exception):
    def __init__(self, executable, source, out, err):
        self.executable = executable
        self.source = source
        self.out = out
        self.err = err


class InterpreterInfo:
    runnable = True

    def __init__(self, name, executable, version_info, sysplatform):
        assert executable and version_info
        self.name = name
        self.executable = executable
        self.version_info = version_info
        self.sysplatform = sysplatform

    def __str__(self):
        return "<executable at %s, version_info %s>" % (
            self.executable, self.version_info)


class NoInterpreterInfo:
    runnable = False

    def __init__(self, name, executable=None,
                 out=None, err="not found"):
        self.name = name
        self.executable = executable
        self.version_info = None
        self.out = out
        self.err = err

    def __str__(self):
        if self.executable:
            return "<executable at %s, not runnable>"
        else:
            return "<executable not found for: %s>" % self.name

if sys.platform != "win32":
    @hookimpl
    def tox_get_python_executable(envconfig):
        return py.path.local.sysfind(envconfig.basepython)

else:
    @hookimpl
    def tox_get_python_executable(envconfig):
        name = envconfig.basepython
        p = py.path.local.sysfind(name)
        if p:
            return p
        actual = None
        # Is this a standard PythonX.Y name?
        m = re.match(r"python(\d)\.(\d)", name)
        if m:
            # The standard names are in predictable places.
            actual = r"c:\python%s%s\python.exe" % m.groups()
        if not actual:
            actual = win32map.get(name, None)
        if actual:
            actual = py.path.local(actual)
            if actual.check():
                return actual
        # The standard executables can be found as a last resort via the
        # Python launcher py.exe
        if m:
            return locate_via_py(*m.groups())

    # Exceptions to the usual windows mapping
    win32map = {
        'python': sys.executable,
        'jython': "c:\jython2.5.1\jython.bat",
    }

    def locate_via_py(v_maj, v_min):
        ver = "-%s.%s" % (v_maj, v_min)
        script = "import sys; print(sys.executable)"
        py_exe = py.path.local.sysfind('py')
        if py_exe:
            try:
                exe = py_exe.sysexec(ver, '-c', script).strip()
            except py.process.cmdexec.Error:
                exe = None
            if exe:
                exe = py.path.local(exe)
                if exe.check():
                    return exe


def pyinfo():
    import sys
    return dict(version_info=tuple(sys.version_info),
                sysplatform=sys.platform)


def sitepackagesdir(envdir):
    from distutils.sysconfig import get_python_lib
    return dict(dir=get_python_lib(prefix=envdir))
