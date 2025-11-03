"""Report format configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tox.plugin import impl

if TYPE_CHECKING:
    from tox.config.sets import ConfigSet, EnvConfigSet
    from tox.session.state import State


@impl
def tox_add_core_config(core_conf: ConfigSet, state: State) -> None:  # noqa: ARG001
    """Add report_format configuration to core config."""
    core_conf.add_config(
        keys=["report_format"],
        of_type=str | None,
        default=None,
        desc="Format for test reports (e.g., 'json', 'xml'). If None, uses default JSON format.",
    )


@impl
def tox_add_env_config(env_conf: EnvConfigSet, state: State) -> None:  # noqa: ARG001
    """Add report_format configuration to environment config (inherits from core if not set)."""
    env_conf.add_config(
        keys=["report_format"],
        of_type=str | None,
        default=lambda conf, _env_name: conf.core["report_format"],
        desc="Format for test reports for this environment (inherits from core config if not set).",
    )


__all__ = ()
