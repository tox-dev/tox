# External facing

0. `Python 3.5+` only.
1. Lazy configuration - everything is materialized only when needed (don't ever generate data that will not be used -
   general speed improvement)
2. built-in wheel build support - no longer generates sdist only
3. library dependency changes are now detected (no longer need to recreate tox-env when adding a new dependency to your
   library) - use PEP-517 meta data generation to acquire these
4. CLI arguments rewrite - all defaults now are override-able either via global ini, or env var
5. allow overriding all configuration values from the cli
6. tox now supports sub-commands - still defaults to run sequential the envs (we plan to add additional commands later -
   e.g. configuration validation):
   - the list envs has migrated to the `list` sub-command from -a (`l` shortcut)
   - the show config has migrated to the `config` sub-command form `--showconfig` (`c` shortcut)
   - the run parallel has migrated to `run-parallel` sub-command form `-p` (`p` shortcut)
   - the run sequential has migrated to `run` sub-command form non other commands (`r` shortcut)
7. while executing subprocess calls the standard error no longer gets forwarded to the standard output but correctly to
   the standard error (previously this was only true for non captured commands)
8. `basepython` is now a list, the first successfully detected python will be used to generate python environment

# Internal

0. `Python 3.5+` only with type annotated code.
1. Separate core configuration concepts from the ini system (to allow introduction of new configuration)
2. so long `py` my good old friend, use `pathlib` always
3. Introduce the executor concept - replaces action, generalize to avoid ease of replacement with
4. Generalize tox environment concept to make it python agnostic
5. Separate the packaging environments versus run environments
6. Package environments are tied directly to run environments (multiple run environments may share the same packaging
   environment)
7. Use the logging framework to log - drop our custom reporter - default log level is `INFO`
8. Python discovery delegated to virtualenv - due to exposing that in virtualenv is WIP, and dependent on our release we
   vendor it for now
9. rewrite the internal cache log (log more, structured, phased)

```json
{
  "ToxEnv": {
    "name": "py37",
    "type": "VirtualEnvRunner"
  },
  "Python": {
    "version_info": [
      3,
      7,
      4,
      "final",
      0
    ],
    "executable": "/Users/bgabor8/git/github/tox/.tox/dev/bin/python"
  },
  "PythonRun": {
    "deps": [
      "pip==19.2.1"
    ],
    "package_deps": [
      "packaging>=14",
      "pluggy<1,>=0.12.0",
      "appdirs<2,>=1.4.3",
      "virtualenv",
      "importlib-metadata<1,>=0.12; python_version < \"3.8\"",
      "freezegun<1,>=0.3.11",
      "pytest<6,>=4.0.0",
      "pytest-cov<3,>=2.5.1",
      "pytest-mock<2,>=1.10.0"
    ]
  }
}⏎
{
  "ToxEnv": {
    "name": ".package",
    "type": "Pep517VirtualEnvPackageWheel"
  },
  "Python": {
    "version_info": [
      3,
      7,
      4,
      "final",
      0
    ],
    "executable": "/Users/bgabor8/git/github/tox/.tox/dev/bin/python"
  },
  "PythonPackage": {
    "requires": [
      "setuptools >= 40.0.4",
      "setuptools_scm >= 2.0.0, <4",
      "wheel >= 0.29.0"
    ],
    "build-requires": []
  }
}
```

# TODO

- index url support for python pip
- introduce the run log concept
- handle provisioning
- make it parallel safe (packaging + logs)
- Make sure we're config compliant with tox 3 (excluding deprecated features) - CLI compliant is best effort
- Allow plugins generating new tox-environments (this will probably require a in-memory config)
- Rewrite documentation (generate configuration from code)

## Validate rewrite

- provide a pre-commit env generator plugin
- provide a sphinx doc env generator plugin
- Provide a tox environment that uses Docker images instead of virtual environments (this will validate the internal
  refactor)
- migrate some popular tox plugins to the new system (`tox-travis` + `tox-pipenv` + `tox-conda` + `tox-pyenv` +
  `tox-current-env`)
