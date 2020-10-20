from argparse import ArgumentTypeError
from typing import Any


class Override:
    def __init__(self, value: str) -> None:
        split_at = value.find("=")
        if split_at == -1:
            raise ArgumentTypeError(f"override {value} has no = sign in it")
        key = value[:split_at]
        ns_at = key.find(".")
        self.namespace = key[:ns_at]
        self.key = key[ns_at + 1 :]
        self.value = value[split_at + 1 :]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}('{self.namespace}{'.' if self.namespace else ''}{self.key}={self.value}')"

    def __eq__(self, other: Any) -> bool:
        return type(self) == type(other) and (self.namespace, self.key, self.value) == (
            other.namespace,
            other.key,
            other.value,
        )

    def __ne__(self, other: Any) -> bool:
        return not (self == other)
