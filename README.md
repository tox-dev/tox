# tox

[![PyPI](https://img.shields.io/pypi/v/tox)](https://pypi.org/project/tox/)
[![Supported Python
versions](https://img.shields.io/pypi/pyversions/tox.svg)](https://pypi.org/project/tox/)
[![Downloads](https://static.pepy.tech/badge/tox/month)](https://pepy.tech/project/tox)
[![Documentation
status](https://readthedocs.org/projects/tox/badge/?version=latest)](https://tox.readthedocs.io/en/latest/?badge=latest)
[![check](https://github.com/tox-dev/tox/actions/workflows/check.yml/badge.svg)](https://github.com/tox-dev/tox/actions/workflows/check.yml)

`tox` aims to automate and standardize testing in Python. It is part of a larger vision of easing the packaging, testing
and release process of Python software (alongside [pytest](https://docs.pytest.org/en/latest/) and
[devpi](https://www.devpi.net)).

tox is a generic virtual environment management and test command line tool you can use for:

- checking your package builds and installs correctly under different environments (such as different Python
  implementations, versions or installation dependencies),
- running your tests in each of the environments with the test tool of choice,
- acting as a frontend to continuous integration servers, greatly reducing boilerplate and merging CI and shell-based
  testing.

Please read our [user guide](https://tox.wiki/en/latest/user_guide.html#basic-example) for an example and more detailed
introduction, or watch [this YouTube video](https://www.youtube.com/watch?v=SFqna5ilqig) that presents the problem space
and how tox solves it.
