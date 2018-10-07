import textwrap

from setuptools import find_packages, setup

setup(
    name="tox",
    description="virtualenv-based automation of test activities",
    long_description=open("README.rst").read(),
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
    packages=find_packages("src"),
    package_dir={"": "src"},
    entry_points={"console_scripts": ["tox=tox:cmdline", "tox-quickstart=tox._quickstart:main"]},
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    install_requires=[
        "setuptools  >= 30.0.0",
        "pluggy >= 0.3.0, <1",
        "py >= 1.4.17, <2",
        "six >= 1.0.0, <2",
        "virtualenv >= 1.11.2",
        "toml >=0.9.4",
        "filelock >= 3.0.0, <4",
    ],
    setup_requires=["setuptools-scm>2, <4"],  # readthedocs needs it
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
            "sphinxcontrib-autoprogram >= 0.1.5",
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
