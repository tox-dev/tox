from __future__ import annotations

from tox.config.of_type import ConfigConstantDefinition, ConfigDynamicDefinition


def test_config_constant_eq() -> None:
    val_1 = ConfigConstantDefinition(("key",), "description", "value")
    val_2 = ConfigConstantDefinition(("key",), "description", "value")
    assert val_1 == val_2


def test_config_dynamic_eq() -> None:
    def func(name: str) -> str:
        return name  # pragma: no cover

    val_1 = ConfigDynamicDefinition(("key",), "description", str, "default", post_process=func)
    val_2 = ConfigDynamicDefinition(("key",), "description", str, "default", post_process=func)
    assert val_1 == val_2
