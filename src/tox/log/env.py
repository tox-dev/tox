"""Record information about tox environments"""
import sys
from copy import copy
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List

from .command import CommandLog


class EnvLog:
    """Report the status of a tox environment"""

    def __init__(self, name: str, content: Dict[str, Any]) -> None:
        self.command_log = CommandLog([])
        self.name = name
        self.content = content

    def set_python_info(self, python_info: Any) -> None:
        answer = copy(python_info.__dict__)
        answer["executable"] = sys.executable
        self.content["python"] = answer

    def get_command_log(self) -> CommandLog:
        """get the command log for a given group name"""
        return self.command_log

    def set_installed(self, packages: List[str]) -> None:
        self.content["installed_packages"] = packages

    def set_header(self, install_pkg: Path) -> None:
        """
        :param
        """
        self.content["installpkg"] = {
            "sha256": sha256(install_pkg.read_bytes()).hexdigest(),
            "basename": install_pkg.name,
        }
