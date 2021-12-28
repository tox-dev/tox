[![PyPI](https://img.shields.io/pypi/v/tox?style=flat-square)](https://pypi.org/project/tox/)
[![Supported Python
versions](https://img.shields.io/pypi/pyversions/tox.svg)](https://pypi.org/project/tox/)
[![check](https://github.com/tox-dev/tox/actions/workflows/check.yml/badge.svg)](https://github.com/tox-dev/tox/actions/workflows/check.yml)
[![Documentation
status](https://readthedocs.org/projects/tox/badge/?version=latest&style=flat-square)](https://tox.readthedocs.io/en/latest/?badge=latest)
[![Code style:
black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Downloads](https://pepy.tech/badge/tox/month)](https://pepy.tech/project/tox/month)

<a href="https://tox.readthedocs.io">
    <img src="https://raw.githubusercontent.com/tox-dev/tox/master/docs/_static/img/tox.png"
         alt="tox logo"
         height="150px"
         align="right">
</a>

# tox automation project

**Command line driven CI frontend and development task automation tool**

At its core tox provides a convenient way to run arbitrary commands in isolated environments to serve as a single entry
point for build, test and release activities.

tox is highly [configurable](https://tox.readthedocs.io/en/latest/config.html) and
[pluggable](https://tox.readthedocs.io/en/latest/plugins.html).

## Example: run tests with Python 3.7 and Python 3.8

tox is mainly used as a command line tool and needs a `tox.ini` or a `tool.tox` section in `pyproject.toml` containing
the configuration.

To test a simple project that has some tests, here is an example with a `tox.ini` in the root of the project:

```ini
[tox]
envlist = py37,py38

[testenv]
deps = pytest
commands = pytest
```

```console
$ tox

[lots of output from what tox does]
[lots of output from commands that were run]

__________________ summary _________________
  py37: commands succeeded
  py38: commands succeeded
  congratulations :)
```

tox created two `testenvs` - one based on Python 3.7 and one based on Python 3.8, it installed pytest in them and ran the
tests. The report at the end summarizes which `testenvs` have failed and which have succeeded.

**Note:** To learn more about what you can do with tox, have a look at
[the collection of examples in the documentation](https://tox.readthedocs.io/en/latest/examples.html) or
[existing projects using tox](https://github.com/search?l=INI&q=tox.ini+in%3Apath&type=Code).

### How it works

tox creates virtual environments for all configured so-called `testenvs`, it then installs the project and other
necessary dependencies and runs the configured set of commands. See
[system overview](https://tox.readthedocs.io/en/latest/#system-overview) for more details.

<a href="https://tox.readthedocs.io/en/latest/#system-overview">
    <img src="https://raw.githubusercontent.com/tox-dev/tox/master/docs/img/tox_flow.png"
         alt="tox flow"
         width="800px"
         align="center">
</a>

### tox can be used for ...

- creating development environments
- running static code analysis and test tools
- automating package builds
- running tests against the package built by tox
- checking that packages install correctly with different Python versions/interpreters
- unifying Continuous Integration and command line based testing
- building and deploying project documentation
- releasing a package to PyPI or any other platform
- limit: your imagination

### Documentation

Documentation for tox can be found at [Read The Docs](https://tox.readthedocs.org).

### Communication and questions

For the fastest and interactive feedback please join our
[![Discord](https://img.shields.io/discord/802911963368783933?style=flat-square)](https://discord.gg/edtj86wzBX) server.
If you have questions or suggestions you can first check if they have already been answered or discussed on our
[issue tracker](https://github.com/tox-dev/tox/issues?utf8=%E2%9C%93&q=is%3Aissue+sort%3Aupdated-desc+label%3A%22type%3Aquestion+%3Agrey_question%3A%22+).
On [Stack Overflow (tagged with `tox`)](https://stackoverflow.com/questions/tagged/tox).

### Contributing

Contributions are welcome. See [contributing](https://github.com/tox-dev/tox/blob/master/CONTRIBUTING.rst) and our
[Contributor Covenant Code of Conduct](https://github.com/tox-dev/tox/blob/master/CODE_OF_CONDUCT.md).

Currently, the [code](https://github.com/tox-dev/tox) and the [issues](https://github.com/tox-dev/tox/issues) are hosted
on GitHub.

The project is licensed under [MIT](https://github.com/tox-dev/tox/blob/master/LICENSE).
