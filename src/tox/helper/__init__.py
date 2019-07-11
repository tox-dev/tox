from pathlib import Path

HERE = Path(__file__).absolute().parent


def script(name: str):
    return HERE / name


def isolated_builder():
    return script("build_isolated.py")


def wheel_meta():
    return script("wheel_meta.py")


def build_requires():
    return script("build_requires.py")
