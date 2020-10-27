"""Define configuration options that are part of the core tox configurations"""
from pathlib import Path
from typing import cast

from tox.config.sets import ConfigSet
from tox.config.source.api import EnvList
from tox.plugin.impl import impl


@impl
def tox_add_core_config(core: ConfigSet) -> None:
    core.add_config(
        keys=["work_dir", "toxworkdir"],
        of_type=Path,
        # here we pin to .tox4 to be able to use in parallel with v3 until final release
        default=lambda conf, _: cast(Path, conf.core["tox_root"]) / ".tox4",
        desc="working directory",
    )
    core.add_config(
        keys=["temp_dir"],
        of_type=Path,
        default=lambda conf, _: cast(Path, conf.core["tox_root"]) / ".temp",
        desc="temporary directory cleaned at start",
    )
    core.add_config(
        keys=["env_list", "envlist"],
        of_type=EnvList,
        default=EnvList([]),
        desc="define environments to automatically run",
    )
    core.add_config(
        keys=["skip_missing_interpreters"],
        of_type=bool,
        default=True,
        desc="skip missing interpreters",
    )
