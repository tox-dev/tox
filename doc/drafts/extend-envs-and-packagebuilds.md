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

This could then be used to hae virtualenv, conda, nixos, docker, pyenv, rpm, deb, etc. builds and tie them to concrete test environments.

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
  (creating 16 processe on a dual core machine might be overkill)
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

### Feature - builddef 

This feature shall allow to specify how to build an artifact in a specific build definition (builddef).

Currently tox uses the current python interpreter to build the artifact (python package) and thus
does not allow to freely choose the interpreter to build with.
This means that as of now build environment and test environment are different by design.

Support for different build definitions is implemented by individual tox plugins.
This would result in a collection of plugins supporting different build definitions (e.g. conda, pyenv, docker, rpm)

Default behavior:

To keep backwards-compatibility, a python package is built with the python interpreter tox is executed with,
using sdist. This does not require any builddef specification in tox.ini.
