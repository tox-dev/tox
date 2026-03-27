# tox

tox is a command-line driven CI frontend and development task automation tool for Python. It automates and standardizes testing by managing virtual environments, installing dependencies, and running test commands across multiple Python versions.

## Primary Language

Python (3.10+). Build system: Hatchling with hatch-vcs for versioning.

## Project Structure

```
src/tox/              # Main source code (src layout)
  config/             # Configuration parsing (CLI args, tox.toml, tox.ini, pyproject.toml, setup.cfg)
    cli/              # CLI argument parsing and help generation
    loader/           # Config value loading and interpolation
    source/           # Config file discovery and reading (INI, TOML, setup.cfg)
  execute/            # Command execution subsystem (subprocess management, streaming)
    local_sub_process/  # Local subprocess execution backend
  journal/            # Run journaling (JSON result recording)
  plugin/             # Plugin system built on pluggy (entry-point discovery, hook specs)
  session/            # Session management (environment selection, state)
    cmd/              # Built-in commands (run, list, depends, devenv, exec, quickstart, show-config)
      run/            # The main `tox run` command implementation
      show_config/    # Config introspection command
  tox_env/            # Test environment abstraction layer
    python/           # Python-specific environment logic
      pip/            # pip installer backend
      virtual_env/    # virtualenv-based environment creation
    api.py            # Base ToxEnv API (the core abstraction)
    runner.py         # RunToxEnv for running commands in environments
    package.py        # PackageToxEnv for building packages
  provision.py        # Self-provisioning (ensuring correct tox version)
  report.py           # Output reporting and logging
  run.py              # Main entry point (tox.run:run)
tests/                # pytest test suite (~89 test files, mirrors src/ structure)
docs/                 # Sphinx documentation (RST + Furo theme)
  changelog/          # Towncrier changelog fragments
tasks/                # Release automation scripts
typestubs/            # Type stubs for dependencies without inline types
tox.toml              # tox's own tox configuration (dogfooding)
```

## Key Commands

```bash
# Run the full test suite (via tox)
tox run -e py

# Run tests directly with pytest (faster iteration)
pytest tests/ -n auto

# Run fast tests only (no integration, no slow, no coverage)
tox run -e fast

# Lint and format (pre-commit with ruff)
tox run -e fix

# Type checking with ty
tox run -e type

# Build documentation
tox run -e docs

# Run a specific test file
pytest tests/config/test_main.py -n auto

# Check package metadata
tox run -e pkg_meta

# Set up dev environment
tox run -e dev
```

## Code Style

- **Formatter/Linter:** Ruff (line length 120, preview mode enabled, `ALL` rules with specific exclusions)
- **Required import:** Every module must start with `from __future__ import annotations`
- **isort:** First-party packages are `tox` and `tests`, enforced via ruff's isort config
- **Type hints:** Required everywhere. The project uses `ty` for type checking (Python 3.14 target). Type stubs live in `typestubs/`
- **Pre-commit hooks:** ruff-check, ruff-format, codespell, pyproject-fmt, prettier (for non-Python files), docstrfmt (RST docstrings, 120 char line length)
- **Docstrings:** RST format (Sphinx-compatible). Formatted with docstrfmt
- **Test style:** pytest with pytest-xdist (parallel), pytest-mock, pytest-timeout (30s default). Markers: `integration`, `slow`
- **Coverage:** Minimum 88% required (covdefaults plugin)

## Architecture

### Core Concepts

1. **Plugin System (pluggy):** tox is built on pluggy. All major extension points are hooks. Plugins register via `[project.entry-points.tox]` in pyproject.toml. Local plugins can be defined in `toxfile.py`.

2. **Configuration Sources:** tox reads config from multiple formats (tox.toml, tox.ini, pyproject.toml `[tool.tox]`, setup.cfg) via a unified loader abstraction. Config values support substitution, environment variable references, and cross-references.

3. **ToxEnv Hierarchy:**
   - `ToxEnv` (base) -> `Python` (Python-specific) -> `VirtualEnv` (virtualenv-based)
   - `RunToxEnv` (for running test commands) and `PackageToxEnv` (for building packages) extend the base
   - Environments are registered via the plugin system

4. **Session Flow:** CLI args -> Config parsing -> Environment selection (`env_select.py`) -> Provisioning check -> Command handler dispatch -> Environment creation -> Command execution -> Result reporting

5. **Execution Model:** Commands run in subprocesses with output streaming. The execute subsystem handles process lifecycle, timeouts, and output capture.

### Key Design Patterns

- **Lazy evaluation:** Config values are computed on demand, not eagerly
- **Plugin-first:** Core functionality is implemented as internal plugins where possible
- **Environment isolation:** Each test environment is fully isolated via virtualenv
- **Self-provisioning:** tox can provision itself if the running version doesn't meet `requires`

## Important Notes

- tox dogfoods itself: `tox.toml` at the repo root is its own tox config
- The `src` layout is used (code under `src/tox/`, not top-level `tox/`)
- Changelog entries use towncrier: add fragments to `docs/changelog/` as `{issue_number}.{type}.rst`
- Fragment types: `feature`, `bugfix`, `doc`, `removal`, `misc`
- Python 3.10 is the minimum supported version
- The project uses `uv` for faster dependency resolution in CI

---

*Generated by [ai-ready](https://github.com/lunacompsia-oss/ai-ready)*
