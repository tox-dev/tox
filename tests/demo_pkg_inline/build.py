"""
Please keep this file Python 2.7 compatible.
See https://tox.readthedocs.io/en/rewrite/development.html#code-style-guide
"""
import os
import sys
import tarfile
from textwrap import dedent
from zipfile import ZipFile

name = "demo_pkg_inline"
pkg_name = name.replace("_", "-")

version = "1.0.0"
dist_info = "{}-{}.dist-info".format(name, version)
logic = "{}/__init__.py".format(name)
metadata = "{}/METADATA".format(dist_info)
wheel = "{}/WHEEL".format(dist_info)
record = "{}/RECORD".format(dist_info)
content = {
    logic: "def do():\n    print('greetings from {}')".format(name),
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
    wheel: """
        Wheel-Version: 1.0
        Generator: {}-{}
        Root-Is-Purelib: true
        Tag: py{}-none-any
       """.format(
        name,
        version,
        sys.version_info[0],
    ),
    "{}/top_level.txt".format(dist_info): name,
    record: """
        {0}/__init__.py,,
        {1}/METADATA,,
        {1}/WHEEL,,
        {1}/top_level.txt,,
        {1}/RECORD,,
       """.format(
        name,
        dist_info,
    ),
}


def build_wheel(wheel_directory, metadata_directory=None, config_settings=None):  # noqa: U100
    base_name = "{}-{}-py{}-none-any.whl".format(name, version, sys.version_info[0])
    path = os.path.join(wheel_directory, base_name)
    with ZipFile(path, "w") as zip_file_handler:
        for arc_name, data in content.items():  # pragma: no branch
            zip_file_handler.writestr(arc_name, dedent(data).strip())
    print("created wheel {}".format(path))
    return base_name


def get_requires_for_build_wheel(config_settings=None):  # noqa: U100
    return []  # pragma: no cover # only executed in non-host pythons


def build_sdist(sdist_directory, config_settings=None):  # noqa: U100
    result = "{}-{}.tar.gz".format(name, version)  # pragma: win32 cover
    with tarfile.open(os.path.join(sdist_directory, result), "w:gz") as tar:  # pragma: win32 cover
        root = os.path.dirname(os.path.abspath(__file__))  # pragma: win32 cover
        tar.add(os.path.join(root, "build.py"), "build.py")  # pragma: win32 cover
        tar.add(os.path.join(root, "pyproject.toml"), "pyproject.toml")  # pragma: win32 cover
    return result  # pragma: win32 cover


def get_requires_for_build_sdist(config_settings=None):  # noqa: U100
    return []  # pragma: no cover # only executed in non-host pythons
