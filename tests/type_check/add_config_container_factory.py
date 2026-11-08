from __future__ import annotations

from tox.config.sets import ConfigSet
from tox.util.typing_compat import override


class EnvDockerConfigSet(ConfigSet):
    @override
    def register_config(self) -> None:
        def factory(  # simplint: ignore[SMP602]  # the factory accepts any container name
            container_name: object,  # simplint: ignore[SMP602]  # the factory accepts any container name
        ) -> str:
            raise NotImplementedError

        self.add_config(
            keys=["k"],
            of_type=list[str],
            default=[],
            desc="desc",
            factory=factory,
        )
