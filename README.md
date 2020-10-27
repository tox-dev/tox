[![check](https://github.com/tox-dev/tox/workflows/check/badge.svg)](https://github.com/tox-dev/tox/actions?query=workflow%3Acheck)
[![codecov](https://codecov.io/gh/tox-dev/tox/branch/rewrite/graph/badge.svg)](https://codecov.io/gh/tox-dev/tox/branch/rewrite)
[![Code style:
black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Rewrite branch

<a href="https://tox.readthedocs.io">
    <img src="https://raw.githubusercontent.com/tox-dev/tox/master/docs/_static/img/tox.png"
         alt="tox logo"
         height="150px"
         align="right">
</a>

You've arrived at the rewrite branch. This is a fresh start for tox in which we aim to create a better implementation
for what tox is. The broad goal is to:

- use modern Python with type annotations (`3.6+` only)
- be more flexible in from where we take our configuration (proper `pyproject.toml` support besides our canonical
  `tox.ini` file)
- a better interface to plug and play your own python environment (historically tox was designed to work with the
  `virtualenv` project, but we want to be able to use instead `conda`, `Docker`, OS package manager, remote machines,
  etc.)
- first class support for non-sdist packages (in python land e.g. wheels)
- ability to plugin support for other languages that follow the build/install/test paradigm (e.g. node)
- make it more flexible (ability to override any value via the CLI)
- make it faster (improve interpreter discovery, lazy configuration manifestation, and many more).

**Compatibility wise we aim to be (excluding some weird edge cases) configuration file compatible with tox 3. We'll not
be API compatible though (all plugins will break).**

### Documentation

To be done.

### Communication and questions

For now reach out to [Bernat Gabor](https://github.com/gaborbernat/) directly.

### Contributing

Contributions are welcome, though expect a lot of rough edges at this early point of development. See
[contributing](https://github.com/tox-dev/tox/blob/master/CONTRIBUTING.rst) and our
[Contributor Covenant Code of Conduct](https://github.com/tox-dev/tox/blob/master/CODE_OF_CONDUCT.md). Currently the
[code](https://github.com/tox-dev/tox) and the [issues](https://github.com/tox-dev/tox/issues) are hosted on Github. The
project is licensed under [MIT](https://github.com/tox-dev/tox/blob/master/LICENSE).
