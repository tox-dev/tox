# Extension of environment handling and building packages

Issue reference: #338

*Notes from a discussion at the pytest sprint 2016*

Goal: drive building of packages and the environments needed to test them, exercising the tests and report the results for more than just virtualenvs and python virtualenvs

### Problems

* No concept of mapping environments to specific packages (versioned packages)
* no control over when it happens for specific environment
* no control over how it happens (e.g. which python interpreter is used to create the package)
* No way of triggering build only if there is an environment that needs a specific build trigger it only if an environment actually needs it
* package definition that might match on everything might be a problem for which environments test? Not clear?

### Solution

It should be possible to build other kinds of packages than just the standard sdist and it should also be possible to create different kinds of builds that can be used from different environments. To make this possible there has to be some concept of factorized package definitions and a way to match these factorized builds to environments with a similar way of matching like what is in place already to generate environments. sdist would for example would match to a "sdist" factor to only be matched against virtualenvs as the default.

This could then be used to have virtualenv, conda, nixos, docker, pyenv, rpm, deb, etc. builds and tie them to concrete test environments.

To summarize - we would need a:

    * packagedef (how to build a package)
    * envdef (how to build an environment)
    * way of matching envs to concrete packages (at package definition level) (e.g `{py27,py34}-{win32,linux}-{venv,conda,pyenv}-[...]`)

## Beginnings of configuration examples (not thought out yet)

    [tox]
    envlist={py,27,py34}-{win32, linux}-{conda,virtualenv}

    [packagedef:sdist]
    # how to build (e.g. {py27,py34}-{sdist})
    # how to match (e.g. {py27,py34}-{sdist})

    [packagedef:conda]
    # how to build (e.g. {py27,py34}-{conda})
    # how to match (e.g. {py27,py34}-{conda})

    [packagedef:wheel]
    # how to build
    # how to match

#### integrate detox

* reporting in detox is minimal (would need to improve)
* restricting processes would be necessary depending on power of the machine
  (creating 16 processes on a dual-core machine might be overkill)
* port it from eventlets to threads?

### Concrete use case conda integration (started by Bruno)

* Asynchronicity / detox not taken into account yet
* Conda activation might do anything (change filesys, start DBs)
* Can I activate environments in parallel
* Packages would need to be created (from conda.yml)
* Activation is a problem


### Unsorted discussion notes

* Simplify for the common case: most packages are universal, so it should be simple
one to one relationship from environment to directory
* Floris: metadata driven. Package has metadata to the env with what env it is compatible
* Holger: configuration driven. explicitly configuring which packages should be used (default sdist to be used, overridable by concrete env)
* Ronny: "package definitions" (this package, this setup command) + matching definitions (matching packages (with wildcards) for environments)


## Proposal

This feature shall allow one to specify how plugins can specify new types of package formats and environments to run test
commands in.

Such plugins would take care of setting up the environment, create packages and run test commands using hooks provided
by tox. The actual knowledge how to create a certain package format is implement in the plugin.

Plugin decides which is the required python interpreter to use in order to create the relevant package format.


```ini
[tox]
plugins=conda # virtualenv plugin is builtin; intention here is to bail out early in case the specified plugins
              # are not installed
envlist=py27,py35

[testenv]
package_formats=            # new option to specify wanted package formats for test environment using tox factors feature
                            # defaults to "sdist" if not set
    py35: sdist wheel conda # names here are provided by plugins (reserved keywords)
    py27: sdist conda
commands = py.test
```

Listing tox environments (`tox --list`) would display the following output:

```
(sdist) py27
(conda) py27
(sdist) py35
(wheel) py35
(conda) py35
```

To remain backward-compatible, the package format will not be displayed if only a single package format is specified.



How to skip building a package for a specific factor?

Illustrate how to exclude a certain package format for a factor:

```ini
[tox]
plugins=conda
envlist=py27,py35,py27-xdist

[testenv]
commands = py.test
package_formats=sdist wheel conda
exclude_package_formats=        # new option which filters out packages
    py27-xdist: wheel
```

or possibly using the negated factor condition support:

```ini
[tox]
plugins=conda
envlist=py27,py35,py27-xdist

[testenv]
commands = py.test
package_formats=
    sdist
    !py27,!xdist: wheel
    conda
```

Output of `tox --list`:

```
(sdist) py27
(wheel) py27
(conda) py27
(sdist) py35
(wheel) py35
(conda) py35
(sdist) py27-xdist
(conda) py27-xdist
```


### Implementation Details

```
tox_package_formats() -> ['conda']   # ['sdist', 'wheel']
tox_testenv_create(env_meta, package_type) -> # creates an environment for given package, using
                                                  # information from env_meta (like .envdir)
                                                  # returns: an "env" object which is forwarded to the next hooks
tox_testenv_install(env_meta, package_type, env) -> # installs deps and package into environment
tox_testenv_runtest(env_meta, package_type, env) -> # activates environment and runs test commands

tox_testenv_updated(env_meta, package_type) ->  # returns True if the environment is already up to date
                                                # otherwise, tox will remove the environment completely and
                                                # create a new one
```
