"""Report format configuration."""

from __future__ import annotations

from tox.plugin import impl


@impl
def tox_add_core_config(core_conf, state) -> None:  # noqa: ARG001
    """Add report_format configuration to core config."""
    core_conf.add_config(
        keys=["report_format"],
        of_type=str | None,
        default=None,
        desc="Format for test reports (e.g., 'json', 'xml'). If None, uses default JSON format.",
    )


@impl
def tox_add_env_config(env_conf, state) -> None:  # noqa: ARG001
    """Add report_format configuration to environment config (inherits from core if not set)."""
    env_conf.add_config(
        keys=["report_format"],
        of_type=str | None,
        default=lambda conf, env_name: conf.core["report_format"],
        desc="Format for test reports for this environment (inherits from core config if not set).",
    )


__all__ = ()
