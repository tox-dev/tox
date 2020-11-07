"""Record information about tox environments"""
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List

from .command import CommandJournal


class EnvJournal:
    """Report the status of a tox environment"""

    def __init__(self, enabled: bool, name: str, content: Dict[str, Any]) -> None:
        self._enabled = enabled
        self.command_log = CommandJournal([])
        self.name = name
        self._content = content

    def get_command_log(self) -> CommandJournal:
        """get the command log for a given group name"""
        return self.command_log

    def set_installed(self, packages: List[str]) -> None:
        self._content["installed_packages"] = packages

    def set_header(self, install_pkg: Path) -> None:
        """
        :param
        """
        self._content["installpkg"] = {
            "sha256": sha256(install_pkg.read_bytes()).hexdigest(),
            "basename": install_pkg.name,
        }

    def __setitem__(self, key: str, value: Any) -> None:
        self._content[key] = value

    @property
    def content(self) -> Dict[str, Any]:
        return self._content

    def __bool__(self) -> bool:
        return self._enabled
