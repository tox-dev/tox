import sys
import py
from tox import __version__ as toxver
import json


class ResultLog:

    def __init__(self, dict=None):
        if dict is None:
            dict = {}
        self.dict = dict
        self.dict.update({"reportversion": "1", "toxversion": toxver})
        self.dict["platform"] = sys.platform
        self.dict["host"] = py.std.socket.getfqdn()

    def set_header(self, installpkg):
        """
        :param py.path.local installpkg: Path ot the package.
        """
        self.dict["installpkg"] = dict(
            md5=installpkg.computehash("md5"),
            sha256=installpkg.computehash("sha256"),
            basename=installpkg.basename,
        )

    def get_envlog(self, name):
        testenvs = self.dict.setdefault("testenvs", {})
        d = testenvs.setdefault(name, {})
        return EnvLog(self, name, d)

    def dumps_json(self):
        return json.dumps(self.dict, indent=2)

    @classmethod
    def loads_json(cls, data):
        return cls(json.loads(data))


class EnvLog:
    def __init__(self, reportlog, name, dict):
        self.reportlog = reportlog
        self.name = name
        self.dict = dict

    def set_python_info(self, pythonexecutable):
        pythonexecutable = py.path.local(pythonexecutable)
        out = pythonexecutable.sysexec("-c",
                                       "import sys; "
                                       "print(sys.executable);"
                                       "print(list(sys.version_info)); "
                                       "print(sys.version)")
        lines = out.splitlines()
        executable = lines.pop(0)
        version_info = eval(lines.pop(0))
        version = "\n".join(lines)
        self.dict["python"] = dict(
            executable=executable,
            version_info=version_info,
            version=version)

    def get_commandlog(self, name):
        l = self.dict.setdefault(name, [])
        return CommandLog(self, l)

    def set_installed(self, packages):
        self.dict["installed_packages"] = packages


class CommandLog:
    def __init__(self, envlog, list):
        self.envlog = envlog
        self.list = list

    def add_command(self, argv, output, retcode):
        d = {}
        self.list.append(d)
        d["command"] = argv
        d["output"] = output
        d["retcode"] = str(retcode)
        return d
