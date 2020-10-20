from argparse import Action, ArgumentParser, Namespace
from typing import Any, List, Optional, Sequence, Union, cast

from tox.config.source.ini.convert import StrConvert


def env_list_flag(parser: ArgumentParser) -> None:
    class ToxEnvList(Action):
        def __call__(
            self,
            parser: ArgumentParser,  # noqa
            args: Namespace,
            values: Union[str, Sequence[Any], None],
            option_string: Optional[str] = None,
        ) -> None:
            list_envs = StrConvert().to(cast(str, values), of_type=List[str])
            setattr(args, self.dest, list_envs)

    parser.add_argument(
        "-e",
        dest="env",
        help="tox environment(s) to run",
        action=ToxEnvList,
        default=None,
        of_type=Optional[List[str]],
    )
