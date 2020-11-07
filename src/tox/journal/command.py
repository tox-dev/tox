"""Record commands executed by tox"""
from typing import Dict, List, Union

CommandDict = Dict[str, Union[int, str, List[str]]]


class CommandJournal:
    """Report commands interacting with third party tools"""

    def __init__(self, container: List[CommandDict]):
        self.entries = container

    def add_command(self, argv: List[str], output: str, error: str, retcode: int) -> CommandDict:
        data: CommandDict = {"command": argv, "output": output, "retcode": retcode, "error": error}
        self.entries.append(data)
        return data


__all__ = (
    "CommandJournal",
    "CommandDict",
)
