"""Generate json report of a tox run"""
import json
import socket
import sys
from typing import List, cast

from tox.version import __version__

from .command import CommandDict, CommandLog
from .env import EnvLog


class ResultLog:
    """The result of a tox session"""

    def __init__(self) -> None:
        command_log: List[CommandDict] = []
        self.command_log = CommandLog(command_log)
        self.content = {
            "reportversion": "1",
            "toxversion": __version__,
            "platform": sys.platform,
            "host": socket.getfqdn(),
            "commands": command_log,
        }

    @classmethod
    def from_json(cls, data: str) -> "ResultLog":
        result = cls()
        result.content = json.loads(data)
        result.command_log = CommandLog(cast(List[CommandDict], result.content["commands"]))
        return result

    def get_envlog(self, name: str) -> EnvLog:
        """Return the env log of an environment (create on first call)"""
        return EnvLog(name, {})

    def dumps_json(self) -> str:
        """Return the json dump of the current state, indented"""
        return json.dumps(self.content, indent=2)
