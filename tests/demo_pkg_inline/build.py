import sys
import tarfile
from pathlib import Path
from textwrap import dedent
from zipfile import ZipFile

name = "demo_pkg_inline"
pkg_name = name.replace("_", "-")

version = "1.0.0"
dist_info = f"{name}-{version}.dist-info"

content = {
    f"{name}/__init__.py": f"def do():\n    print('greetings from {name}')",
    f"{dist_info}/METADATA": f"""
        Metadata-Version: 2.1
        Name: {pkg_name}
        Version: {version}
        Summary: UNKNOWN
        Home-page: UNKNOWN
        Author: UNKNOWN
        Author-email: UNKNOWN
        License: UNKNOWN
        Platform: UNKNOWN

        UNKNOWN
       """,
    f"{dist_info}/WHEEL": f"""
        Wheel-Version: 1.0
        Generator: {name}-{version}
        Root-Is-Purelib: true
        Tag: py3-none-any
       """,
    f"{dist_info}/top_level.txt": name,
    f"{dist_info}/RECORD": f"""
        {name}/__init__.py,,
        {dist_info}/METADATA,,
        {dist_info}/WHEEL,,
        {dist_info}/top_level.txt,,
        {dist_info}/RECORD,,
       """,
}


def build_wheel(wheel_directory, metadata_directory=None, config_settings=None):
    base_name = f"{name}-{version}-py{sys.version_info.major}-none-any.whl"
    path = Path(wheel_directory) / base_name
    with ZipFile(str(path), "w") as zip_file_handler:
        for arc_name, data in content.items():
            zip_file_handler.writestr(zinfo_or_arcname=arc_name, data=dedent(data).strip())
    print(f"created wheel {path}")
    return base_name


def get_requires_for_build_wheel(config_settings):
    return []  # pragma: no cover # only executed in non-host pythons


def build_sdist(sdist_directory, config_settings=None):
    result = f"{name}-{version}.tar.gz"
    with tarfile.open(str(Path(sdist_directory) / result), "w:gz") as tar:
        root = Path(__file__).parent
        tar.add(str(root / "build.py"), arcname="build.py")
        tar.add(str(root / "pyproject.toml"), arcname="pyproject.toml")
    return result


def get_requires_for_build_sdist(config_settings):
    return []  # pragma: no cover # only executed in non-host pythons
