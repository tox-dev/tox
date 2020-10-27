from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, cast

from tox.config.main import Config
from tox.tox_env.runner import RunToxEnv

if TYPE_CHECKING:
    from tox.config.cli.parse import ParsedOptions


class State:
    def __init__(
        self,
        conf: Config,
        tox_envs: Dict[str, RunToxEnv],
        opt_parse: "ParsedOptions",
        args: Sequence[str],
    ) -> None:
        self.conf = conf
        self.tox_envs = tox_envs
        options, handlers = opt_parse
        self.options = options
        self.handlers = handlers
        self.args = args

    @property
    def env_list(self) -> List[str]:
        tox_env_keys = cast(Optional[List[str]], self.options.env)
        if tox_env_keys is None:
            tox_env_keys = cast(List[str], self.conf.core["env_list"])
        return tox_env_keys
