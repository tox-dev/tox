from __future__ import absolute_import, unicode_literals

import json
import subprocess

from .command import CommandLog


class EnvLog(object):
    """Report the status of a tox environment"""

    def __init__(self, result_log, name, dict):
        self.reportlog = result_log
        self.name = name
        self.dict = dict

    def set_python_info(self, python_executable):
        cmd = [
            str(python_executable),
            "-c",
            "import sys; import json;"
            "print(json.dumps({"
            "'executable': sys.executable,"
            "'version_info': list(sys.version_info),"
            "'version': sys.version}))",
        ]
        result = subprocess.check_output(cmd, universal_newlines=True)
        self.dict["python"] = json.loads(result)

    def get_commandlog(self, name):
        """get the command log for a given group name"""
        data = self.dict.setdefault(name, [])
        return CommandLog(self, data)

    def set_installed(self, packages):
        self.dict["installed_packages"] = packages

    def set_header(self, installpkg):
        """
        :param py.path.local installpkg: Path ot the package.
        """
        self.dict["installpkg"] = {
            "md5": installpkg.computehash("md5"),
            "sha256": installpkg.computehash("sha256"),
            "basename": installpkg.basename,
        }
