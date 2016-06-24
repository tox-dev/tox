# Extension of environment handling and building packages

Goal drive building of packages and the environments needed to test them, exercising the tests and report the results for more than just virtualenvs and python virtualenvs

Necessary to implement:

* sdist refactoring (con concept for multiple package creations (e.g. wheels, conda, ...))
* environment system extension

## Use case: conda

* general package def (how to build the package)
* general environment def (how to build an environment)
* matching environments to package definition (at package definition level) (e.g {py27,py34}-{venv,conda,pyenv}-[...])

## Problems

* package definition that might match on everything might be a problem for which environments test? Not clear?
* sdist would need a "sdist" factor to only be matched against virtualenvs

## section examples

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

## Next release (3.0)

* ship what we have
* Plan for next major release

## sdist refatoring

* Needs concept of mapping environments to specific packages (versioned packages)
* no control over when it happens for specific environment
* no control over how it happens (e.g. which python interpreter is used to create the package)
* trigger it only if an environment actually needs it

### Ideas

* Simplify for the common case: most packages are universal, so it should be simple
one to one relationship from environment to directory
* Floris: metadata driven. Package has metadata to the env with what env it is compatible
* Holger: configuration driven. explicitly configuring which packages should be used (default sdist to be used, overridable by concrete env)
* Ronny: "package definitions" (this pacakge, this setup command) + matching definitions (matching packages (with wldcards) for environemnts)

## integrate detox

* reporting in detox is minimal (would need to improve)
* restricting processes would be necessary depending on power of the machine
  (creating 16 processe on a dual core machine might be overkill)
* port it from eventlets to threads?

## Extend environment integrations

Different kinds and combinations of environments

* Virtualenv, conda, nixos, docker, pyenv, rpm, deb, npm ...
* Code needs to change a lot
* need to be documunted properly

### conda integration

* Asynchronicity / detox not taken into account yet
* Conda activation might do anything (change filesys, start DBs)
* Can I activate environments in parallel
* Packages would need to be created (from conda.yml)
* Activation is a problem

### pyenv integration

* ?

# Questions

* list all environments from command line (not just the ones from envlist)

# Ideas

* sync command line options and actual documentation
* General way of running tests in an already existing environment

# Problems

* Per python version wheels are not taken into account yet
