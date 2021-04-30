```
[tox]
envlist=py27,py35

[testenv]
commands= py.test --timeout=180 {posargs:tests}
deps=pytest>=2.3.5
    pytest-timeout

# USE CASE 1: plain conda, with deps on tox.ini
create_env_command = conda create --prefix {envdir} python={python_version}
install_command = conda install --prefix {envdir} {opts} {packages}
list_dependencies_command = conda list --prefix {envdir}

# deprecated: see tox_create_popen hook
linux:env_activate_command=source activate {envdir}
win:env_activate_command=activate.bat {envdir}

# USE CASE 2: plain conda, using requirements.txt
install_command = conda install --prefix {envdir} {opts} --file requirements.txt

# USE CASE 3: conda env
create_env_command = conda env create --prefix {envdir} python={python_version} --file environment.yml
install_command =

[testenv]
type=virtualenv
type=venv
type=conda
type=conda-reqs
type=conda-env
```

1. Create a new ``create_env_command`` option.
2. Create a new ``env_activate_command`` option (also consider how to make that platform dependent).
2. New substitution variable: {python_version} ('3.5', '2.7', etc')
3. env type concept: different types change the default options.

1. tox_addoption can now add new "testenv" sections to tox.ini:
```
[virtualenv]
[conda]
[venv]
```
2. extend hooks:
```
    * tox_addoption
    * tox_configure
    for each requested env in config:
      tox_testenv_up_to_date(envmeta)
      tox_testenv_create(envmeta)
      tox_testenv_install_deps(envmeta, env)
      tox_runtest_pre(envmeta, env)
      tox_runtest(envmeta, env, popen)
      tox_runtest_post(envmeta, env)
```

3. separate virtualenv details from "VirtualEnv" class into a plugin.

```
[tox]
envlist={py27,py35}-{sdist,wheel,conda}

[package-sdist]
command = python setup.py sdist

[package-wheel]
command = python setup.py bdist_wheel

[package-conda]
command = conda build ./conda-recipe

[testenv:{sdist,wheel}]
commands = py.test

[testenv:conda]
packages = sdist,wheel
commands = py.test --conda-only
```

* tox_addoption
* tox_get_python_executable
* tox_configure
for each requested env in config:
  tox_testenv_create(envmeta)
  tox_testenv_install_deps(envmeta, env)
  tox_runtest_pre(envmeta, env)
  tox_runtest(envmeta, env, popen)
  tox_runtest_post(envmeta, env)
