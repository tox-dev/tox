"""
Contains helper scripts.
"""
from pathlib import Path

HERE = Path(__file__).absolute().parent


def script(name: str) -> Path:
    return HERE / name


def isolated_builder() -> Path:
    return script("build_isolated.py")


def wheel_meta() -> Path:
    return script("wheel_meta.py")


def build_requires() -> Path:
    return script("build_requires.py")
