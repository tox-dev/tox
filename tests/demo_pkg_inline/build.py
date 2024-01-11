"""
Please keep this file Python 2.7 compatible.
See https://tox.readthedocs.io/en/rewrite/development.html#code-style-guide
"""

from __future__ import annotations

import os
import sys
import tarfile
from pathlib import Path
from textwrap import dedent
from zipfile import ZipFile

name = "demo_pkg_inline"
pkg_name = name.replace("_", "-")

version = "1.0.0"
dist_info = f"{name}-{version}.dist-info"
logic = f"{name}/__init__.py"
plugin = f"{name}/example_plugin.py"
entry_points = f"{dist_info}/entry_points.txt"
metadata = f"{dist_info}/METADATA"
wheel = f"{dist_info}/WHEEL"
record = f"{dist_info}/RECORD"
content = {
    logic: f"def do():\n    print('greetings from {name}')",
    plugin: """
        try:
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
        """,
}
metadata_files = {
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
}


def build_wheel(
    wheel_directory: str,
    config_settings: dict[str, str] | None = None,  # noqa: ARG001
    metadata_directory: str | None = None,
) -> str:
    base_name = f"{name}-{version}-py{sys.version_info[0]}-none-any.whl"
    path = Path(wheel_directory) / base_name
    with ZipFile(str(path), "w") as zip_file_handler:
        for arc_name, data in content.items():  # pragma: no branch
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
    print(f"created wheel {path}")  # noqa: T201
    return base_name


def get_requires_for_build_wheel(config_settings: dict[str, str] | None = None) -> list[str]:  # noqa: ARG001
    return []  # pragma: no cover # only executed in non-host pythons


if os.environ.get("BACKEND_HAS_EDITABLE"):

    def build_editable(
        wheel_directory: str,
        config_settings: dict[str, str] | None = None,
        metadata_directory: str | None = None,
    ) -> str:
        return build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory: str, config_settings: dict[str, str] | None = None) -> str:  # noqa: ARG001
    result = f"{name}-{version}.tar.gz"  # pragma: win32 cover
    with tarfile.open(str(Path(sdist_directory) / result), "w:gz") as tar:  # pragma: win32 cover
        root = Path(__file__).parent  # pragma: win32 cover
        tar.add(str(root / "build.py"), "build.py")  # pragma: win32 cover
        tar.add(str(root / "pyproject.toml"), "pyproject.toml")  # pragma: win32 cover
    return result  # pragma: win32 cover


def get_requires_for_build_sdist(config_settings: dict[str, str] | None = None) -> list[str]:  # noqa: ARG001
    return []  # pragma: no cover # only executed in non-host pythons
