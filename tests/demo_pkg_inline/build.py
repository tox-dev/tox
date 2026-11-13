"""Please keep this file Python 2.7 compatible. See https://tox.readthedocs.io/en/rewrite/development.html#code-style-guide"""

from __future__ import annotations

import os
import sys
import tarfile
from pathlib import Path
from textwrap import dedent
from types import MappingProxyType
from typing import Final
from zipfile import ZipFile

name: Final[str] = "demo_pkg_inline"
pkg_name: Final[str] = name.replace("_", "-")

version: Final[str] = "1.0.0"
dist_info: Final[str] = f"{name}-{version}.dist-info"
logic: Final[str] = f"{name}/__init__.py"
plugin: Final[str] = f"{name}/example_plugin.py"
entry_points: Final[str] = f"{dist_info}/entry_points.txt"
metadata: Final[str] = f"{dist_info}/METADATA"
wheel: Final[str] = f"{dist_info}/WHEEL"
record: Final[str] = f"{dist_info}/RECORD"
content = {
    logic: f"def do():\n    print('greetings from {name}')",
    plugin: """
        try:
            from tox.config.cli.parser import ToxParser
            from tox.plugin import impl
            from tox.tox_env.python.virtual_env.runner import VirtualEnvRunner
            from tox.tox_env.register import ToxEnvRegister
        except ImportError:
            pass
        else:
            class ExampleVirtualEnvRunner(VirtualEnvRunner):
                @staticmethod
                def id() -> str:
                    return "example"
            @impl
            def tox_register_tox_env(register: ToxEnvRegister) -> None:
                register.add_run_env(ExampleVirtualEnvRunner)
            @impl
            def tox_add_option(parser: ToxParser) -> None:
                parser.add_argument("--demo-plugin", action="store_true", help="demo plugin flag")
        """,
}
metadata_files: Final[MappingProxyType[str, str]] = MappingProxyType({
    entry_points: f"""
        [tox]
        example = {name}.example_plugin""",
    metadata: """
        Metadata-Version: 2.1
        Name: {}
        Version: {}
        Summary: UNKNOWN
        Home-page: UNKNOWN
        Author: UNKNOWN
        Author-email: UNKNOWN
        License: UNKNOWN
        {}
        Platform: UNKNOWN

        UNKNOWN
       """.format(
        pkg_name,
        version,
        "\n        ".join(os.environ.get("METADATA_EXTRA", "").split("\n")),
    ),
    wheel: f"""
        Wheel-Version: 1.0
        Generator: {name}-{version}
        Root-Is-Purelib: true
        Tag: py{sys.version_info[0]}-none-any
       """,
    f"{dist_info}/top_level.txt": name,
    record: f"""
        {name}/__init__.py,,
        {dist_info}/METADATA,,
        {dist_info}/WHEEL,,
        {dist_info}/top_level.txt,,
        {dist_info}/RECORD,,
       """,
})


def get_requires_for_build_wheel(  # interface signature
    config_settings: dict[str, str] | None = None,  # ruff:ignore[unused-function-argument]  # interface signature
) -> list[str]:
    return []  # pragma: no cover # only executed in non-host pythons


if os.environ.get("BACKEND_HAS_EDITABLE"):

    def build_editable(
        wheel_directory: str,
        config_settings: dict[str, str] | None = None,
        metadata_directory: str | None = None,
    ) -> str:
        return build_wheel(wheel_directory, config_settings, metadata_directory)


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, str] | None = None,  # ruff:ignore[unused-function-argument]  # interface signature
    metadata_directory: str | None = None,
) -> str:
    base_name = f"{name}-{version}-py{sys.version_info[0]}-none-any.whl"
    path = Path(wheel_directory) / base_name
    with ZipFile(str(path), "w") as zip_file_handler:
        for arc_name, data in content.items():  # pragma: no branch  # other outcome untested
            zip_file_handler.writestr(arc_name, dedent(data).strip())
        if metadata_directory is not None:
            for sub_directory, _, filenames in os.walk(metadata_directory):
                for filename in filenames:
                    zip_file_handler.write(
                        str(Path(metadata_directory) / sub_directory / filename),
                        str(Path(sub_directory) / filename),
                    )
        else:
            for arc_name, data in metadata_files.items():
                zip_file_handler.writestr(arc_name, dedent(data).strip())
    print(f"created wheel {path}")  # ruff:ignore[print]  # test output
    return base_name


def build_sdist(  # interface signature
    sdist_directory: str,
    config_settings: dict[str, str] | None = None,  # ruff:ignore[unused-function-argument]  # interface signature
) -> str:
    result = f"{name}-{version}.tar.gz"  # pragma: win32 cover
    with tarfile.open(str(Path(sdist_directory) / result), "w:gz") as tar:  # pragma: win32 cover
        root = Path(__file__).parent  # pragma: win32 cover
        tar.add(str(root / "build.py"), "build.py")  # pragma: win32 cover
        tar.add(str(root / "pyproject.toml"), "pyproject.toml")  # pragma: win32 cover
    return result  # pragma: win32 cover


def get_requires_for_build_sdist(  # interface signature
    config_settings: dict[str, str] | None = None,  # ruff:ignore[unused-function-argument]  # interface signature
) -> list[str]:
    return []  # pragma: no cover # only executed in non-host pythons
