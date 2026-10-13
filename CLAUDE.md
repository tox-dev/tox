# tox

Development commands, all defined as environments in `tox.toml`:

- Run the test suite: `tox -e 3.15`; pass pytest arguments after `--`, for example `tox -e 3.15 -- -k test_name`.
- Lint and auto-format the whole repository with the pre-commit hooks: `tox -e fix`.
- Type check with ty, mypy and pyrefly: `tox -e type`; `tox -e type-min` repeats it on Python 3.11, the minimum.
- Build the documentation, treating warnings as errors: `tox -e docs`.
- Build the sdist and wheel and validate their metadata: `tox -e pkg_meta`.
