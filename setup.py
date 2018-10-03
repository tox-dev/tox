import io
import re
import sys
import textwrap

import setuptools


def has_environment_marker_support():
    """
    Tests that setuptools has support for PEP-426 environment marker support.

    The first known release to support it is 0.7 (and the earliest on PyPI seems to be 0.7.2
    so we're using that), see: https://pythonhosted.org/setuptools/history.html#id142

    References:

    * https://wheel.readthedocs.org/en/latest/index.html#defining-conditional-dependencies
    * https://www.python.org/dev/peps/pep-0426/#environment-markers
    """
    import pkg_resources

    try:
        v = pkg_resources.parse_version(setuptools.__version__)
        return v >= pkg_resources.parse_version("0.7.2")
    except Exception as e:
        sys.stderr.write("Could not test setuptool's version: {}\n".format(e))
        return False


def fix_changelog(text):
    # first we need to prune the include draft, we don't have a draft for PyPi release
    text = text.replace(".. include:: ../_draft.rst", "")
    # now we need to fix the user custom directives: user
    pattern = re.compile(r":user:`(\w+)`")
    text = pattern.sub(r"`\1 <https://github.com/\1>`_", text)
    return text


def get_long_description():
    with io.open("README.rst", encoding="utf-8") as f:
        with io.open("CHANGELOG.rst", encoding="utf-8") as g:
            return u"{}\n\n{}".format(f.read(), fix_changelog(g.read()))


def main():
    setuptools.setup(
        name="tox",
        description="virtualenv-based automation of test activities",
        long_description=get_long_description(),
        url="https://tox.readthedocs.org/",
        use_scm_version={
            "write_to": "src/tox/version.py",
            "write_to_template": textwrap.dedent(
                """
                 # coding: utf-8
                 from __future__ import unicode_literals

                 __version__ = {version!r}
                 """
            ).lstrip(),
        },
        license="https://opensource.org/licenses/MIT",
        platforms=["unix", "linux", "osx", "cygwin", "win32"],
        author="holger krekel",
        author_email="holger@merlinux.eu",
        packages=setuptools.find_packages("src"),
        package_dir={"": "src"},
        entry_points={
            "console_scripts": ["tox=tox:cmdline", "tox-quickstart=tox._quickstart:main"]
        },
        python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
        setup_requires=[
            "setuptools-scm"
        ],  # needed for https://github.com/pypa/readme_renderer/issues/118
        install_requires=[
            "setuptools  >= 30.0.0",
            "pluggy >= 0.3.0, <1",
            "py >= 1.4.17, <2",
            "six >= 1.0.0, <2",
            "virtualenv >= 1.11.2",
            "toml >=0.9.4",
        ],
        extras_require={
            "testing": [
                "pytest >= 3.0.0, <4",
                "pytest-cov >= 2.5.1, <3",
                "pytest-mock >= 1.10.0, <2",
                "pytest-timeout >= 1.3.0, <2",
                "pytest-xdist >= 1.22.2, <2",
                "pytest-randomly >= 1.2.3, <2",
            ],
            "docs": [
                "sphinx >= 1.8.0, < 2",
                "towncrier >= 18.5.0",
                "pygments-github-lexers >= 0.0.5",
            ],
        },
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "Framework :: tox",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: MIT License",
            "Operating System :: POSIX",
            "Operating System :: Microsoft :: Windows",
            "Operating System :: MacOS :: MacOS X",
            "Topic :: Software Development :: Testing",
            "Topic :: Software Development :: Libraries",
            "Topic :: Utilities",
        ]
        + [
            ("Programming Language :: Python :: {}".format(x))
            for x in "2 2.7 3 3.4 3.5 3.6 3.7".split()
        ],
    )


if __name__ == "__main__":
    main()
