.. _changelog:

Changelog history
=================

Versions follow `Semantic Versioning <https://semver.org/>`_ (``<major>.<minor>.<patch>``).
Backward incompatible (breaking) changes will only be introduced in major versions
with advance notice in the **Deprecations** section of releases.

.. include:: _draft.rst

.. towncrier release notes start

v3.24.5 (2021-12-29)
Bugfixes
^^^^^^^^

- Fixed an issue where ``usedevelop`` would cause an invocation error if setup.py does not exist. -- by :user:`VincentVanlaer`
  `#2197 <https://github.com/tox-dev/tox/issues/2197>`_


v3.24.4 (2021-09-16)
--------------------

Bugfixes
^^^^^^^^

- Fixed handling of ``-e ALL`` in parallel mode by ignoring the ``ALL`` in subprocesses -- by :user:`guahki`.
  `#2167 <https://github.com/tox-dev/tox/issues/2167>`_
- Prevent tox from using a truncated interpreter when using
  ``TOX_LIMITED_SHEBANG`` -- by :user:`jdknight`.
  `#2208 <https://github.com/tox-dev/tox/issues/2208>`_


Documentation
^^^^^^^^^^^^^

- Enabled the use of the favicon in the Sphinx docs first
  introduced in :pull:`764` but not integrated fully
  -- :user:`webknjaz`
  `#2177 <https://github.com/tox-dev/tox/issues/2177>`_


v3.24.3 (2021-08-21)
--------------------

Bugfixes
^^^^^^^^

- ``--parallel`` reports now show ASCII OK/FAIL/SKIP lines when full Unicode output is not available - by :user:`brettcs`
  `#1421 <https://github.com/tox-dev/tox/issues/1421>`_


Miscellaneous
^^^^^^^^^^^^^

- Started enforcing valid references in Sphinx docs -- :user:`webknjaz`
  `#2168 <https://github.com/tox-dev/tox/issues/2168>`_


v3.24.2 (2021-08-18)
--------------------

Bugfixes
^^^^^^^^

- include ``LC_ALL`` to implicit list of passenv variables - by :user:`ssbarnea`
  `#2162 <https://github.com/tox-dev/tox/issues/2162>`_


v3.24.1 (2021-07-31)
--------------------

Bugfixes
^^^^^^^^

- ``get_requires_for_build_sdist`` hook (PEP 517) is assumed to return an empty list if left unimplemented by the backend build system - by :user:`oczkoisse`
  `#2130 <https://github.com/tox-dev/tox/issues/2130>`_


Documentation
^^^^^^^^^^^^^

- The documentation of ``install_command`` now also mentions that you can provide arbitrary commands - by :user:`jugmac00`
  `#2081 <https://github.com/tox-dev/tox/issues/2081>`_


v3.24.0 (2021-07-14)
--------------------

Bugfixes
^^^^^^^^

- ``--devenv`` no longer modifies the directory in which the ``.tox`` environment is provisioned - by :user:`isaac-ped`
  `#2065 <https://github.com/tox-dev/tox/issues/2065>`_
- Fix show config when the package names are not in canonical form - by :user:`gaborbernat`.
  `#2103 <https://github.com/tox-dev/tox/issues/2103>`_


Documentation
^^^^^^^^^^^^^

- Extended environment variables section - by :user:`majiang`
  `#2036 <https://github.com/tox-dev/tox/issues/2036>`_


Miscellaneous
^^^^^^^^^^^^^

- ``tox`` no longer shows deprecation warnings for ``distutils.sysconfig`` on
  Python 3.10 - by :user:`9999years`
  `#2100 <https://github.com/tox-dev/tox/issues/2100>`_


v3.23.1 (2021-05-05)
--------------------

Bugfixes
^^^^^^^^

- Distinguish between normal Windows Python and MSYS2 Python when looking for
  virtualenv executable path.  Adds os.sep to :class:`~tox.interpreters.InterpreterInfo`
  - by :user:`jschwartzentruber`
  `#1982 <https://github.com/tox-dev/tox/issues/1982>`_
- Fix a ``tox-conda`` isolation build bug - by :user:`AntoineD`.
  `#2056 <https://github.com/tox-dev/tox/issues/2056>`_


Documentation
^^^^^^^^^^^^^

- Update examples in the documentation to use ``setenv`` in the ``[testenv]`` sections, not wrongly in the ``[tox]`` main section.
  - by :user:`AndreyNautilus`
  `#1999 <https://github.com/tox-dev/tox/issues/1999>`_


Miscellaneous
^^^^^^^^^^^^^

- Enable building tox with ``setuptools_scm`` 6+ by :user:`hroncok`
  `#1984 <https://github.com/tox-dev/tox/issues/1984>`_


v3.23.0 (2021-03-03)
--------------------

Features
^^^^^^^^

- tox can now be invoked with a new ``--no-provision`` flag that prevents provision,
  if :conf:`requires` or :conf:`minversion` are not satisfied,
  tox will fail;
  if a path is specified as an argument to the flag
  (e.g. as ``tox --no-provision missing.json``) and provision is prevented,
  provision metadata are written as JSON to that path - by :user:`hroncok`
  `#1921 <https://github.com/tox-dev/tox/issues/1921>`_
- Unicode support in ``pyproject.toml`` - by :user:`domdfcoding`
  `#1940 <https://github.com/tox-dev/tox/issues/1940>`_


v3.22.0 (2021-02-16)
--------------------

Features
^^^^^^^^

- The value of the :conf:`requires` configuration option is now exposed via
  the :class:`tox.config.Config` object - by :user:`hroncok`
  `#1918 <https://github.com/tox-dev/tox/issues/1918>`_


v3.21.4 (2021-02-02)
--------------------

Bugfixes
^^^^^^^^

- Adapt tests not to assume the ``easy_install`` command exists, as it was removed from ``setuptools`` 52.0.0+ - by :user:`hroncok`
  `#1893 <https://github.com/tox-dev/tox/issues/1893>`_


v3.21.3 (2021-01-28)
--------------------

Bugfixes
^^^^^^^^

- Fix a killed tox (via SIGTERM) leaving the commands subprocesses running
  by handling it as if it were a KeyboardInterrupt - by :user:`dajose`
  `#1772 <https://github.com/tox-dev/tox/issues/1772>`_


v3.21.2 (2021-01-19)
--------------------

Bugfixes
^^^^^^^^

- Newer coverage tools update the ``COV_CORE_CONTEXT`` environment variable, add it to the list of environment variables
  that can change in our pytest plugin - by :user:`gaborbernat`.
  `#1854 <https://github.com/tox-dev/tox/issues/1854>`_


v3.21.1 (2021-01-13)
--------------------

Bugfixes
^^^^^^^^

- Fix regression that broke using install_command in config replacements - by :user:`jayvdb`
  `#1777 <https://github.com/tox-dev/tox/issues/1777>`_
- Fix regression parsing posargs default containing colon. - by :user:`jayvdb`
  `#1785 <https://github.com/tox-dev/tox/issues/1785>`_


Features
^^^^^^^^

- Prevent .tox in envlist - by :user:`jayvdb`
  `#1684 <https://github.com/tox-dev/tox/issues/1684>`_


Miscellaneous
^^^^^^^^^^^^^

- Enable building tox with ``setuptools_scm`` 4 and 5 by :user:`hroncok`
  `#1799 <https://github.com/tox-dev/tox/issues/1799>`_


v3.21.0 (2021-01-08)
--------------------

Bugfixes
^^^^^^^^

- Fix the false ``congratulations`` message that appears when a ``KeyboardInterrupt`` occurs during package installation. - by :user:`gnikonorov`
  `#1453 <https://github.com/tox-dev/tox/issues/1453>`_
- Fix ``platform`` support for ``install_command``. - by :user:`jayvdb`
  `#1464 <https://github.com/tox-dev/tox/issues/1464>`_
- Fixed regression in v3.20.0 that caused escaped curly braces in setenv
  to break usage of the variable elsewhere in tox.ini. - by :user:`jayvdb`
  `#1690 <https://github.com/tox-dev/tox/issues/1690>`_
- Prevent ``{}`` and require ``{:`` is only followed by ``}``. - by :user:`jayvdb`
  `#1711 <https://github.com/tox-dev/tox/issues/1711>`_
- Raise ``MissingSubstitution`` on access of broken ini setting. - by :user:`jayvdb`
  `#1716 <https://github.com/tox-dev/tox/issues/1716>`_


Features
^^^^^^^^

- Allow \{ and \} in default of {env:key:default}. - by :user:`jayvdb`
  `#1502 <https://github.com/tox-dev/tox/issues/1502>`_
- Allow {posargs} in setenv. - by :user:`jayvdb`
  `#1695 <https://github.com/tox-dev/tox/issues/1695>`_
- Allow {/} to refer to os.sep. - by :user:`jayvdb`
  `#1700 <https://github.com/tox-dev/tox/issues/1700>`_
- Make parsing [testenv] sections in setup.cfg official. - by :user:`mauvilsa`
  `#1727 <https://github.com/tox-dev/tox/issues/1727>`_
- Relax importlib requirement to allow 3.0.0 or any newer version - by
  :user:`pkolbus`
  `#1763 <https://github.com/tox-dev/tox/issues/1763>`_


Documentation
^^^^^^^^^^^^^

- Document more info about using ``platform`` setting. - by :user:`prakhargurunani`
  `#1144 <https://github.com/tox-dev/tox/issues/1144>`_
- Replace ``indexserver`` in documentation with environment variables - by :user:`ziima`.
  `#1357 <https://github.com/tox-dev/tox/issues/1357>`_
- Document that the ``passenv`` environment setting is case insensitive. - by :user:`gnikonorov`
  `#1534 <https://github.com/tox-dev/tox/issues/1534>`_


v3.20.1 (2020-10-09)
--------------------

Bugfixes
^^^^^^^^

- Relax importlib requirement to allow version<3 - by :user:`usamasadiq`
  `#1682 <https://github.com/tox-dev/tox/issues/1682>`_


v3.20.0 (2020-09-01)
--------------------

Bugfixes
^^^^^^^^

- Allow hyphens and empty factors in generative section name. - by :user:`tyagdit`
  `#1636 <https://github.com/tox-dev/tox/issues/1636>`_
- Support for PEP517 in-tree build backend-path key in ``get-build-requires``. - by :user:`nizox`
  `#1654 <https://github.com/tox-dev/tox/issues/1654>`_
- Allow escaping curly braces in setenv. - by :user:`mkenigs`
  `#1656 <https://github.com/tox-dev/tox/issues/1656>`_


Features
^^^^^^^^

- Support for comments within ``setenv`` and environment files via the ``files|`` prefix. - by :user:`gaborbernat`
  `#1667 <https://github.com/tox-dev/tox/issues/1667>`_


v3.19.0 (2020-08-06)
--------------------

Bugfixes
^^^^^^^^

- skip ``setup.cfg`` if it has no ``tox:tox`` namespace - by :user:`hroncok`
  `#1045 <https://github.com/tox-dev/tox/issues/1045>`_


Features
^^^^^^^^

- Implement support for building projects
  having :pep:`517#in-tree-build-backends` ``backend-path`` setting -
  by :user:`webknjaz`
  `#1575 <https://github.com/tox-dev/tox/issues/1575>`_
- Don't require a tox config file for ``tox --devenv`` - by :user:`hroncok`
  `#1643 <https://github.com/tox-dev/tox/issues/1643>`_


Documentation
^^^^^^^^^^^^^

- Fixed grammar in top-level documentation - by :user:`tfurf`
  `#1631 <https://github.com/tox-dev/tox/issues/1631>`_


v3.18.1 (2020-07-28)
--------------------

Bugfixes
^^^^^^^^

- Fix ``TypeError`` when using isolated_build with backends that are not submodules (e.g. ``maturin``)
  `#1629 <https://github.com/tox-dev/tox/issues/1629>`_


v3.18.0 (2020-07-23)
--------------------

Deprecations (removal in next major release)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Add allowlist_externals alias to whitelist_externals (whitelist_externals is now deprecated). - by :user:`dajose`
  `#1491 <https://github.com/tox-dev/tox/issues/1491>`_


v3.17.1 (2020-07-15)
--------------------

Bugfixes
^^^^^^^^

- Fix tests when the ``HOSTNAME`` environment variable is set, but empty string - by :user:`hroncok`
  `#1616 <https://github.com/tox-dev/tox/issues/1616>`_


v3.17.0 (2020-07-14)
--------------------

Features
^^^^^^^^

- The long arguments ``--verbose`` and ``--quiet`` (rather than only their short forms, ``-v`` and ``-q``) are now accepted.
  `#1612 <https://github.com/tox-dev/tox/issues/1612>`_
- The ``ResultLog`` now prefers ``HOSTNAME`` environment variable value (if set) over the full qualified domain name of localhost.
  This makes it possible to disable an undesired DNS lookup,
  which happened on all ``tox`` invocations, including trivial ones - by :user:`hroncok`
  `#1615 <https://github.com/tox-dev/tox/issues/1615>`_


Documentation
^^^^^^^^^^^^^

- Update packaging information for Flit.
  `#1613 <https://github.com/tox-dev/tox/issues/1613>`_


v3.16.1 (2020-06-29)
--------------------

Bugfixes
^^^^^^^^

- Fixed the support for using ``{temp_dir}`` in ``tox.ini`` - by :user:`webknjaz`
  `#1609 <https://github.com/tox-dev/tox/issues/1609>`_


v3.16.0 (2020-06-26)
--------------------

Features
^^^^^^^^

- Allow skipping the package and installation step when passing the ``--skip-pkg-install``. This should be used in pair with the ``--notest``, so you can separate environment setup and test run:

   .. code-block:: console

      tox -e py --notest
      tox -e py --skip-pkg-install

  by :user:`gaborbernat`.
  `#1605 <https://github.com/tox-dev/tox/issues/1605>`_


Miscellaneous
^^^^^^^^^^^^^

- Improve config parsing performance by precompiling commonly used regular expressions - by :user:`brettlangdon`
  `#1603 <https://github.com/tox-dev/tox/issues/1603>`_


v3.15.2 (2020-06-06)
--------------------

Bugfixes
^^^^^^^^

- Add an option to allow a process to suicide before sending the SIGTERM. - by :user:`jhesketh`
  `#1497 <https://github.com/tox-dev/tox/issues/1497>`_
- PyPy 7.3.1 on Windows uses the ``Script`` folder instead of ``bin``. - by :user:`gaborbernat`
  `#1597 <https://github.com/tox-dev/tox/issues/1597>`_


Miscellaneous
^^^^^^^^^^^^^

- Allow to run the tests with pip 19.3.1 once again while preserving the ability to use pip 20.1 - by :user:`hroncok`
  `#1594 <https://github.com/tox-dev/tox/issues/1594>`_


v3.15.1 (2020-05-20)
--------------------

Bugfixes
^^^^^^^^

- ``tox --showconfig`` no longer tries to interpolate '%' signs.
  `#1585 <https://github.com/tox-dev/tox/issues/1585>`_


v3.15.0 (2020-05-02)
--------------------

Bugfixes
^^^^^^^^

- Respect attempts to change ``PATH`` via ``setenv`` - by :user:`aklajnert`.
  `#1423 <https://github.com/tox-dev/tox/issues/1423>`_
- Fix parsing of architecture in python interpreter name. - by :user:`bruchar1`
  `#1542 <https://github.com/tox-dev/tox/issues/1542>`_
- Prevent exception when command is empty. - by :user:`bruchar1`
  `#1544 <https://github.com/tox-dev/tox/issues/1544>`_
- Fix irrelevant Error message for invalid argument when running outside a directory with tox support files by :user:`nkpro2000sr`.
  `#1547 <https://github.com/tox-dev/tox/issues/1547>`_


Features
^^^^^^^^

- Allow parallel mode without arguments. - by :user:`ssbarnea`
  `#1418 <https://github.com/tox-dev/tox/issues/1418>`_
- Allow generative section name expansion. - by :user:`bruchar1`
  `#1545 <https://github.com/tox-dev/tox/issues/1545>`_
- default to passing the env var PIP_EXTRA_INDEX_URL by :user:`georgealton`.
  `#1561 <https://github.com/tox-dev/tox/issues/1561>`_


Documentation
^^^^^^^^^^^^^

- Improve documentation about config by adding tox environment description at start - by :user:`stephenfin`.
  `#1573 <https://github.com/tox-dev/tox/issues/1573>`_


v3.14.6 (2020-03-25)
--------------------

Bugfixes
^^^^^^^^

- Exclude virtualenv dependency versions with known
  regressions (20.0.[0-7]) - by :user:`webknjaz`.
  `#1537 <https://github.com/tox-dev/tox/issues/1537>`_
- Fix ``tox -h`` and ``tox --hi`` shows an error when run outside a directory with tox support files by :user:`nkpro2000sr`.
  `#1539 <https://github.com/tox-dev/tox/issues/1539>`_
- Fix ValueError on ``tox -l`` for a ``tox.ini`` file that does not contain an
  ``envlist`` definition. - by :user:`jquast`.
  `#1343 <https://github.com/tox-dev/tox/issues/1343>`_


v3.14.5 (2020-02-16)
--------------------

Features
^^^^^^^^

- Add ``--discover`` (fallback to ``TOX_DISCOVER`` environment variable via path separator) to inject python executables
  to try as first step of a discovery - note the executable still needs to match the environment by :user:`gaborbernat`.
  `#1526 <https://github.com/tox-dev/tox/issues/1526>`_


v3.14.4 (2020-02-13)
--------------------

Bugfixes
^^^^^^^^

- Bump minimal six version needed to avoid using one incompatible with newer
  virtualenv. - by :user:`ssbarnea`
  `#1519 <https://github.com/tox-dev/tox/issues/1519>`_
- Avoid pypy test failure due to undefined printout var. - by :user:`ssbarnea`
  `#1521 <https://github.com/tox-dev/tox/issues/1521>`_


Features
^^^^^^^^

- Add ``interrupt_timeout`` and ``terminate_timeout`` that configure delay between SIGINT, SIGTERM and SIGKILL when tox is interrupted. - by :user:`sileht`
  `#1493 <https://github.com/tox-dev/tox/issues/1493>`_
- Add ``HTTP_PROXY``, ``HTTPS_PROXY`` and ``NO_PROXY`` to default passenv. - by :user:`pfmoore`
  `#1498 <https://github.com/tox-dev/tox/issues/1498>`_


v3.14.3 (2019-12-27)
--------------------

Bugfixes
^^^^^^^^

- Relax importlib requirement to allow either version 0 or 1 - by :user:`chyzzqo2`
  `#1476 <https://github.com/tox-dev/tox/issues/1476>`_

Miscellaneous
^^^^^^^^^^^^^

- Clarify legacy setup.py error message: python projects should commit to a strong consistency of message regarding packaging. We no-longer tell people to add a setup.py to their already configured pep-517 project, otherwise it could imply that pyproject.toml isn't as well supported and recommended as it truly is - by :user:`graingert`
  `#1478 <https://github.com/tox-dev/tox/issues/1478>`_

v3.14.2 (2019-12-02)
--------------------

Bugfixes
^^^^^^^^

- Fix fallback to global configuration when running in Jenkins. - by :user:`daneah`
  `#1428 <https://github.com/tox-dev/tox/issues/1428>`_
- Fix colouring on windows: colorama is a dep. - by :user:`1138-4EB`
  `#1471 <https://github.com/tox-dev/tox/issues/1471>`_


Miscellaneous
^^^^^^^^^^^^^

- improve performance with internal lookup of Python version information - by :user:`blueyed`
  `#1462 <https://github.com/tox-dev/tox/issues/1462>`_
- Use latest version of importlib_metadata package - by :user:`kammala`
  `#1472 <https://github.com/tox-dev/tox/issues/1472>`_
- Mark poetry related tests as xfail since its dependency pyrsistent won't install in ci due to missing wheels/build deps. - by :user:`RonnyPfannschmidt`
  `#1474 <https://github.com/tox-dev/tox/issues/1474>`_


v3.14.1 (2019-11-13)
--------------------

Bugfixes
^^^^^^^^

- fix reporting of exiting due to (real) signals - by :user:`blueyed`
  `#1401 <https://github.com/tox-dev/tox/issues/1401>`_
- Bump minimal virtualenv to 16.0.0 to improve own transitive
  deps handling in some ancient envs. — by :user:`webknjaz`
  `#1429 <https://github.com/tox-dev/tox/issues/1429>`_
- Adds ``CURL_CA_BUNDLE``, ``REQUESTS_CA_BUNDLE``, ``SSL_CERT_FILE`` to the default passenv values. - by :user:`ssbarnea`
  `#1437 <https://github.com/tox-dev/tox/issues/1437>`_
- Fix nested tox execution in the parallel mode by separating the environment
  variable that let's tox know it is invoked in the parallel mode
  (``_TOX_PARALLEL_ENV``) from the variable that informs the tests that tox is
  running in parallel mode (``TOX_PARALLEL_ENV``).
  — by :user:`hroncok`
  `#1444 <https://github.com/tox-dev/tox/issues/1444>`_
- Fix provisioning from a pyvenv interpreter. — by :user:`kentzo`
  `#1452 <https://github.com/tox-dev/tox/issues/1452>`_


Deprecations (removal in next major release)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Python ``3.4`` is no longer supported. — by :user:`gaborbernat`
  `#1456 <https://github.com/tox-dev/tox/issues/1456>`_


v3.14.0 (2019-09-03)
--------------------

Bugfixes
^^^^^^^^

- Fix ``PythonSpec`` detection of ``python3.10`` - by :user:`asottile`
  `#1374 <https://github.com/tox-dev/tox/issues/1374>`_
- Fix regression failing to detect future and past ``py##`` factors  - by :user:`asottile`
  `#1377 <https://github.com/tox-dev/tox/issues/1377>`_
- Fix ``current_tox_py`` for ``pypy`` / ``pypy3`` - by :user:`asottile`
  `#1378 <https://github.com/tox-dev/tox/issues/1378>`_
- Honor environment markers in ``requires`` list - by :user:`asottile`
  `#1380 <https://github.com/tox-dev/tox/issues/1380>`_
- improve recreate check by allowing directories containing ``.tox-config1`` (the marker file created by tox) - by :user:`asottile`
  `#1383 <https://github.com/tox-dev/tox/issues/1383>`_
- Recognize correctly interpreters that have suffixes (like python3.7-dbg).
  `#1415 <https://github.com/tox-dev/tox/issues/1415>`_


Features
^^^^^^^^

- Add support for minor versions with multiple digits ``tox -e py310`` works for ``python3.10`` - by :user:`asottile`
  `#1374 <https://github.com/tox-dev/tox/issues/1374>`_
- Remove dependence on ``md5`` hashing algorithm - by :user:`asottile`
  `#1384 <https://github.com/tox-dev/tox/issues/1384>`_


Documentation
^^^^^^^^^^^^^

- clarify behaviour if recreate is set to false - by :user:`PJCampi`
  `#1399 <https://github.com/tox-dev/tox/issues/1399>`_


Miscellaneous
^^^^^^^^^^^^^

- ￼Fix relative URLs to files in the repo in ``.github/PULL_REQUEST_TEMPLATE.md`` — by :user:`webknjaz`
  `#1363 <https://github.com/tox-dev/tox/issues/1363>`_
- Replace ``importlib_metadata`` backport with ``importlib.metadata``
  from the standard library on Python ``3.8+`` - by :user:`hroncok`
  `#1367 <https://github.com/tox-dev/tox/issues/1367>`_
- Render the change fragment help on the ``docs/changelog/`` directory view on GitHub — by :user:`webknjaz`
  `#1370 <https://github.com/tox-dev/tox/issues/1370>`_


v3.13.2 (2019-07-01)
--------------------

Bugfixes
^^^^^^^^

- on venv cleanup: add explicit check for pypy venv to make it possible to recreate it - by :user:`obestwalter`
  `#1355 <https://github.com/tox-dev/tox/issues/1355>`_
- non canonical names within :conf:`requires` cause infinite provisioning loop - by :user:`gaborbernat`
  `#1359 <https://github.com/tox-dev/tox/issues/1359>`_


v3.13.1 (2019-06-25)
--------------------

Bugfixes
^^^^^^^^

- Fix isolated build double-requirement - by :user:`asottile`.
  `#1349 <https://github.com/tox-dev/tox/issues/1349>`_


v3.13.0 (2019-06-24)
--------------------

Bugfixes
^^^^^^^^

- tox used Windows shell rules on non-Windows platforms when transforming
  positional arguments to a string - by :user:`barneygale`.
  `#1336 <https://github.com/tox-dev/tox/issues/1336>`_


Features
^^^^^^^^

- Replace ``pkg_resources`` with ``importlib_metadata`` for speed - by :user:`asottile`.
  `#1324 <https://github.com/tox-dev/tox/issues/1324>`_
- Add the ``--devenv ENVDIR`` option for creating development environments from ``[testenv]`` configurations - by :user:`asottile`.
  `#1326 <https://github.com/tox-dev/tox/issues/1326>`_
- Refuse to delete ``envdir`` if it doesn't look like a virtualenv - by :user:`asottile`.
  `#1340 <https://github.com/tox-dev/tox/issues/1340>`_


v3.12.1 (2019-05-23)
--------------------

Bugfixes
^^^^^^^^

- Ensure ``TOX_WORK_DIR`` is a native string in ``os.environ`` - by :user:`asottile`.
  `#1313 <https://github.com/tox-dev/tox/issues/1313>`_
- Fix import and usage of ``winreg`` for python2.7 on windows - by :user:`asottile`.
  `#1315 <https://github.com/tox-dev/tox/issues/1315>`_
- Fix Windows selects incorrect spec on first discovery - by :user:`gaborbernat`
  `#1317 <https://github.com/tox-dev/tox/issues/1317>`_


v3.12.0 (2019-05-23)
--------------------

Bugfixes
^^^^^^^^

- When using ``--parallel`` with ``--result-json`` the test results are now included the same way as with serial runs - by :user:`fschulze`
  `#1295 <https://github.com/tox-dev/tox/issues/1295>`_
- Turns out the output of the ``py -0p`` is not stable yet and varies depending on various edge cases. Instead now we read the interpreter values directly from registry via `PEP-514 <https://www.python.org/dev/peps/pep-0514>`_ - by :user:`gaborbernat`.
  `#1306 <https://github.com/tox-dev/tox/issues/1306>`_


Features
^^^^^^^^

- Adding ``TOX_PARALLEL_NO_SPINNER`` environment variable to disable the spinner in parallel mode for the purposes of clean output when using CI tools - by :user:`zeroshift`
  `#1184 <https://github.com/tox-dev/tox/issues/1184>`_


v3.11.1 (2019-05-16)
--------------------

Bugfixes
^^^^^^^^

- When creating virtual environments we no longer ask the python to tell its path, but rather use the discovered path.
  `#1301 <https://github.com/tox-dev/tox/issues/1301>`_


v3.11.0 (2019-05-15)
--------------------

Features
^^^^^^^^

- ``--showconfig`` overhaul:

  - now fully generated via the config parser, so anyone can load it by using the built-in python config parser
  - the ``tox`` section contains all configuration data from config
  - the ``tox`` section contains a ``host_python`` key detailing the path of the host python
  - the ``tox:version`` section contains the versions of all packages tox depends on with their version
  - passing ``-l`` now allows only listing default target envs
  - allows showing config for a given set of tox environments only via the ``-e`` cli flag or the ``TOXENV`` environment
    variable, in this case the ``tox`` and ``tox:version`` section is only shown if at least one verbosity flag is passed

  this should help inspecting the options.
  `#1298 <https://github.com/tox-dev/tox/issues/1298>`_


v3.10.0 (2019-05-13)
--------------------

Bugfixes
^^^^^^^^

- fix for ``tox -l`` command: do not allow setting the ``TOXENV`` or the ``-e`` flag to override the listed default environment variables, they still show up under extra if non defined target - by :user:`gaborbernat`
  `#720 <https://github.com/tox-dev/tox/issues/720>`_
- tox ignores unknown CLI arguments when provisioning is on and outside of the provisioned environment (allowing
  provisioning arguments to be forwarded freely) - by :user:`gaborbernat`
  `#1270 <https://github.com/tox-dev/tox/issues/1270>`_


Features
^^^^^^^^

- Virtual environments created now no longer upgrade pip/wheel/setuptools to the latest version. Instead the start
  packages after virtualenv creation now is whatever virtualenv has bundled in. This allows faster virtualenv
  creation and builds that are easier to reproduce.
  `#448 <https://github.com/tox-dev/tox/issues/448>`_
- Improve python discovery and add architecture support:
   - UNIX:

     - First, check if the tox host Python matches.
     - Second, check if the the canonical name (e.g. ``python3.7``, ``python3``) matches or the base python is an absolute path, use that.
     - Third, check if the the canonical name without version matches (e.g. ``python``, ``pypy``) matches.

   - Windows:

     - First, check if the tox host Python matches.
     - Second, use the ``py.exe`` to list registered interpreters and any of those match.
     - Third, check if the the canonical name (e.g. ``python3.7``, ``python3``) matches or the base python is an absolute path, use that.
     - Fourth, check if the the canonical name without version matches (e.g. ``python``, ``pypy``) matches.
     - Finally, check for known locations (``c:\python{major}{minor}\python.exe``).


  tox environment configuration generation is now done in parallel (to alleviate the slowdown due to extra
  checks).
  `#1290 <https://github.com/tox-dev/tox/issues/1290>`_


v3.9.0 (2019-04-17)
-------------------

Bugfixes
^^^^^^^^

- Fix ``congratulations`` when using ``^C`` during virtualenv creation - by :user:`asottile`
  `#1257 <https://github.com/tox-dev/tox/issues/1257>`_


Features
^^^^^^^^

- Allow having inline comments in :conf:`deps` — by :user:`webknjaz`
  `#1262 <https://github.com/tox-dev/tox/issues/1262>`_


v3.8.6 (2019-04-03)
-------------------

Bugfixes
^^^^^^^^

- :conf:`parallel_show_output` does not work with tox 3.8
  `#1245 <https://github.com/tox-dev/tox/issues/1245>`_


v3.8.5 (2019-04-03)
-------------------

Bugfixes
^^^^^^^^

- the isolated build env now ignores :conf:`sitepackages`, :conf:`deps` and :conf:`description` as these do not make
  sense - by :user:`gaborbernat`
  `#1239 <https://github.com/tox-dev/tox/issues/1239>`_
- Do not print timings with more than 3 decimal digits on Python 3 - by :user:`mgedmin`.
  `#1241 <https://github.com/tox-dev/tox/issues/1241>`_


v3.8.4 (2019-04-01)
-------------------

Bugfixes
^^^^^^^^

- Fix sdist creation on python2.x when there is non-ascii output.
  `#1234 <https://github.com/tox-dev/tox/issues/1234>`_
- fix typos in isolated.py that made it impossible to install package with requirements in pyproject.toml - by :user:`unmade`
  `#1236 <https://github.com/tox-dev/tox/issues/1236>`_


v3.8.3 (2019-03-29)
-------------------

Bugfixes
^^^^^^^^

- don't crash when version information is not available for a proposed base python - by :user:`gaborbernat`
  `#1227 <https://github.com/tox-dev/tox/issues/1227>`_
- Do not print exception traceback when the provisioned tox fails - by :user:`gaborbernat`
  `#1228 <https://github.com/tox-dev/tox/issues/1228>`_


v3.8.2 (2019-03-29)
-------------------

Bugfixes
^^^^^^^^

- using -v and -e connected (as -ve) fails - by :user:`gaborbernat`
  `#1218 <https://github.com/tox-dev/tox/issues/1218>`_
- Changes to the plugin tester module (cmd no longer sets ``PYTHONPATH``), and ``action.popen`` no longer returns the
  command identifier information from within the logs. No public facing changes.
  `#1222 <https://github.com/tox-dev/tox/issues/1222>`_
- Spinner fails in CI on ``UnicodeEncodeError`` - by :user:`gaborbernat`
  `#1223 <https://github.com/tox-dev/tox/issues/1223>`_


v3.8.1 (2019-03-28)
-------------------

Bugfixes
^^^^^^^^

- The ``-eALL`` command line argument now expands the ``envlist`` key and includes all its environment.
  `#1155 <https://github.com/tox-dev/tox/issues/1155>`_
- Isolated build environment dependency overrides were not taken in consideration (and such it inherited the deps
  from the testenv section) - by :user:`gaborbernat`
  `#1207 <https://github.com/tox-dev/tox/issues/1207>`_
- ``--result-json`` puts the command into setup section instead of test (pre and post commands are now also correctly
  put into the commands section) - by :user:`gaborbernat`
  `#1210 <https://github.com/tox-dev/tox/issues/1210>`_
- Set ``setup.cfg`` encoding to UTF-8 as it contains Unicode characters.
  `#1212 <https://github.com/tox-dev/tox/issues/1212>`_
- Fix tox CI, better error reporting when locating via the py fails - by :user:`gaborbernat`
  `#1215 <https://github.com/tox-dev/tox/issues/1215>`_


v3.8.0 (2019-03-27)
-------------------

Bugfixes
^^^^^^^^

- In a posix shell, setting the PATH environment variable to an empty value is equivalent to not setting it at all;
  therefore we no longer if the user sets PYTHONPATH an empty string on python 3.4 or later - by :user:`gaborbernat`.
  `#1092 <https://github.com/tox-dev/tox/issues/1092>`_
- Fixed bug of children process calls logs clashing (log already exists) - by :user:`gaborbernat`
  `#1137 <https://github.com/tox-dev/tox/issues/1137>`_
- Interpreter discovery and virtualenv creation process calls that failed will now print out on the screen their output
  (via the logfile we automatically save) - by :user:`gaborbernat`
  `#1150 <https://github.com/tox-dev/tox/issues/1150>`_
- Using ``py2`` and ``py3`` with a specific ``basepython`` will no longer raise a warning unless the major version conflicts - by :user:`demosdemon`.
  `#1153 <https://github.com/tox-dev/tox/issues/1153>`_
- Fix missing error for ``tox -e unknown`` when tox.ini declares ``envlist``. - by :user:`medmunds`
  `#1160 <https://github.com/tox-dev/tox/issues/1160>`_
- Resolve symlinks with ``toxworkdir`` - by :user:`blueyed`.
  `#1169 <https://github.com/tox-dev/tox/issues/1169>`_
- Interrupting a tox call (e.g. via CTRL+C) now will ensure that spawn child processes (test calls, interpreter discovery,
  parallel sub-instances, provisioned hosts) are correctly stopped before exiting (via the pattern of INTERRUPT - 300 ms,
  TERMINATE - 200 ms, KILL signals)  - by :user:`gaborbernat`
  `#1172 <https://github.com/tox-dev/tox/issues/1172>`_
- Fix a ``ResourceWarning: unclosed file`` in ``Action`` - by :user:`BoboTiG`.
  `#1179 <https://github.com/tox-dev/tox/issues/1179>`_
- Fix deadlock when using ``--parallel`` and having environments with lots of output - by :user:`asottile`.
  `#1183 <https://github.com/tox-dev/tox/issues/1183>`_
- Removed code that sometimes caused a difference in results between ``--parallel`` and ``-p`` when using ``posargs`` - by :user:`timdaman`
  `#1192 <https://github.com/tox-dev/tox/issues/1192>`_


Features
^^^^^^^^

- tox now auto-provisions itself if needed (see :ref:`auto-provision`). Plugins or minimum version of tox no longer
  need to be manually satisfied by the user, increasing their ease of use. - by :user:`gaborbernat`
  `#998 <https://github.com/tox-dev/tox/issues/998>`_
- tox will inject the ``TOX_PARALLEL_ENV`` environment variable, set to the current running tox environment name,
  only when running in parallel mode. - by :user:`gaborbernat`
  `#1139 <https://github.com/tox-dev/tox/issues/1139>`_
- Parallel children now save their output to a disk logfile  - by :user:`gaborbernat`
  `#1143 <https://github.com/tox-dev/tox/issues/1143>`_
- Parallel children now are added to ``--result-json``  - by :user:`gaborbernat`
  `#1159 <https://github.com/tox-dev/tox/issues/1159>`_
- Display pattern and ``sys.platform`` with platform mismatch - by :user:`blueyed`.
  `#1176 <https://github.com/tox-dev/tox/issues/1176>`_
- Setting the environment variable ``TOX_REPORTER_TIMESTAMP`` to ``1`` will enable showing for each output line its delta
  since the tox startup. This can be especially handy when debugging parallel runs.- by :user:`gaborbernat`
  `#1203 <https://github.com/tox-dev/tox/issues/1203>`_


Documentation
^^^^^^^^^^^^^

- Add a ``poetry`` examples to packaging - by :user:`gaborbernat`
  `#1163 <https://github.com/tox-dev/tox/issues/1163>`_


v3.7.0 (2019-01-11)
-------------------

Features
^^^^^^^^

- Parallel mode added (alternative to ``detox`` which is being deprecated), for more details see :ref:`parallel_mode` - by :user:`gaborbernat`.
  `#439 <https://github.com/tox-dev/tox/issues/439>`_
- Added command line shortcut ``-s`` for ``--skip-missing-interpreters`` - by :user:`evandrocoan`
  `#1119 <https://github.com/tox-dev/tox/issues/1119>`_


Deprecations (removal in next major release)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Whitelisting of externals will be mandatory in tox 4: issue a deprecation warning as part of the already existing warning - by :user:`obestwalter`
  `#1129 <https://github.com/tox-dev/tox/issues/1129>`_


Documentation
^^^^^^^^^^^^^

- Clarify explanations in examples and avoid unsupported end line comments - by :user:`obestwalter`
  `#1110 <https://github.com/tox-dev/tox/issues/1110>`_
- Set to PULL_REQUEST_TEMPLATE.md use relative instead of absolute URLs - by :user:`evandrocoan`
  Fixed PULL_REQUEST_TEMPLATE.md path for changelog/examples.rst to docs/changelog/examples.rst - by :user:`evandrocoan`
  `#1120 <https://github.com/tox-dev/tox/issues/1120>`_


v3.6.1 (2018-12-24)
-------------------

Features
^^^^^^^^

- if the packaging phase successfully builds a package set it as environment variable under ``TOX_PACKAGE`` (useful to make assertions on the built package itself, instead of just how it ends up after installation) - by :user:`gaborbernat` (`#1081 <https://github.com/tox-dev/tox/issues/1081>`_)


v3.6.0 (2018-12-13)
-------------------

Bugfixes
^^^^^^^^

- On windows, check ``sys.executable`` before others for interpreter version lookup.  This matches what happens on non-windows. (`#1087 <https://github.com/tox-dev/tox/issues/1087>`_)
- Don't rewrite ``{posargs}`` substitution for absolute paths. (`#1095 <https://github.com/tox-dev/tox/issues/1095>`_)
- Correctly fail ``tox --notest`` when setup fails. (`#1097 <https://github.com/tox-dev/tox/issues/1097>`_)


Documentation
^^^^^^^^^^^^^

- Update Contributor Covenant URL to use https:// - by :user:`jdufresne`. (`#1082 <https://github.com/tox-dev/tox/issues/1082>`_)
- Correct the capitalization of PyPI throughout the documentation - by :user:`jdufresne`. (`#1084 <https://github.com/tox-dev/tox/issues/1084>`_)
- Link to related projects (Invoke and Nox) from the documentation - by :user:`theacodes`. (`#1088 <https://github.com/tox-dev/tox/issues/1088>`_)


Miscellaneous
^^^^^^^^^^^^^

- Include the license file in the wheel distribution - by :user:`jdufresne`. (`#1083 <https://github.com/tox-dev/tox/issues/1083>`_)


v3.5.3 (2018-10-28)
-------------------

Bugfixes
^^^^^^^^

- Fix bug with incorrectly defactorized dependencies - by :user:`bartsanchez` (`#706 <https://github.com/tox-dev/tox/issues/706>`_)
- do the same transformation to ``egg_info`` folders that ``pkg_resources`` does;
  this makes it possible for hyphenated names to use the ``develop-inst-noop`` optimization (cf. 910),
  which previously only worked with non-hyphenated egg names - by
  :user:`hashbrowncipher` (`#1051 <https://github.com/tox-dev/tox/issues/1051>`_)
- previously, if a project's ``setup.py --name`` emitted extra information to
  stderr, tox would capture it and consider it part of the project's name; now,
  emissions to stderr are printed to the console - by :user:`hashbrowncipher` (`#1052 <https://github.com/tox-dev/tox/issues/1052>`_)
- change the way we acquire interpreter information to make it compatible with ``jython`` interpreter, note to create jython envs one needs ``virtualenv > 16.0`` which will be released later :user:`gaborbernat` (`#1073 <https://github.com/tox-dev/tox/issues/1073>`_)


Documentation
^^^^^^^^^^^^^

- document substitutions with additional content starting with a space cannot be alone on a line inside the ini file - by :user:`gaborbernat` (`#437 <https://github.com/tox-dev/tox/issues/437>`_)
- change the spelling of a single word from contrains to the proper word, constraints - by :user:`metasyn` (`#1061 <https://github.com/tox-dev/tox/issues/1061>`_)
- Mention the minimum version required for ``commands_pre``/``commands_post`` support. (`#1071 <https://github.com/tox-dev/tox/issues/1071>`_)


v3.5.2 (2018-10-09)
-------------------

Bugfixes
^^^^^^^^

- session packages are now put inside a numbered directory (instead of prefix numbering it,
  because pip fails when wheels are not named according to
  `PEP-491 <https://www.python.org/dev/peps/pep-0491/#id9>`_, and prefix numbering messes with this)
  - by :user:`gaborbernat` (`#1042 <https://github.com/tox-dev/tox/issues/1042>`_)


Features
^^^^^^^^

- level three verbosity (``-vvv``) show the packaging output - by :user:`gaborbernat` (`#1047 <https://github.com/tox-dev/tox/issues/1047>`_)


v3.5.1 (2018-10-08)
-------------------

Bugfixes
^^^^^^^^

- fix regression with ``3.5.0``: specifying ``--installpkg`` raises ``AttributeError: 'str' object has no attribute 'basename'`` (`#1042 <https://github.com/tox-dev/tox/issues/1042>`_)


v3.5.0 (2018-10-08)
-------------------

Bugfixes
^^^^^^^^

- intermittent failures with ``--parallel--safe-build``, instead of mangling with the file paths now uses a lock to make the package build operation thread safe and is now on by default (``--parallel--safe-build`` is now deprecated) - by :user:`gaborbernat` (`#1026 <https://github.com/tox-dev/tox/issues/1026>`_)


Features
^^^^^^^^

- Added ``temp_dir`` folder configuration (defaults to ``{toxworkdir}/.tmp``) that contains tox
  temporary files. Package builds now create a hard link (if possible, otherwise copy - notably in
  case of Windows Python 2.7) to the built file, and feed that file downstream (e.g. for pip to
  install it). The hard link is removed at the end of the run (what it points though is kept
  inside ``distdir``). This ensures that a tox session operates on the same package it built, even
  if a parallel tox run builds another version. Note ``distdir`` will contain only the last built
  package in such cases. - by :user:`gaborbernat` (`#1026 <https://github.com/tox-dev/tox/issues/1026>`_)


Documentation
^^^^^^^^^^^^^

- document tox environment recreate rules (:ref:`recreate`) - by :user:`gaborbernat` (`#93 <https://github.com/tox-dev/tox/issues/93>`_)
- document inside the ``--help`` how to disable colorized output via the ``PY_COLORS`` operating system environment variable - by :user:`gaborbernat` (`#163 <https://github.com/tox-dev/tox/issues/163>`_)
- document all global tox flags and a more concise format to express default and type - by :user:`gaborbernat` (`#683 <https://github.com/tox-dev/tox/issues/683>`_)
- document command line interface under the config section `cli <https://tox.readthedocs.io/en/latest/config.html?highlight=cli#cli>`_ - by :user:`gaborbernat` (`#829 <https://github.com/tox-dev/tox/issues/829>`_)

v3.4.0 (2018-09-20)
-------------------

Bugfixes
^^^^^^^^

- add ``--exists-action w`` to default pip flags to handle better VCS dependencies (`pip documentation on this <https://pip.pypa.io/en/latest/reference/pip/#exists-action-option>`_) - by :user:`gaborbernat` (`#503 <https://github.com/tox-dev/tox/issues/503>`_)
- instead of assuming the Python version from the base python name ask the interpreter to reveal the version for the ``ignore_basepython_conflict`` flag - by :user:`gaborbernat` (`#908 <https://github.com/tox-dev/tox/issues/908>`_)
- PEP-517 packaging fails with sdist already exists, fixed via ensuring the dist folder is empty before invoking the backend and `pypa/setuptools 1481 <https://github.com/pypa/setuptools/pull/1481>`_ - by :user:`gaborbernat` (`#1003 <https://github.com/tox-dev/tox/issues/1003>`_)


Features
^^^^^^^^

- add ``commands_pre`` and ``commands_post`` that run before and after running
  the ``commands`` (setup runs always, commands only if setup succeeds, teardown always - all
  run until the first failing command)  - by :user:`gaborbernat` (`#167 <https://github.com/tox-dev/tox/issues/167>`_)
- ``pyproject.toml`` config support initially by just inline the tox.ini under ``tool.tox.legacy_tox_ini`` key; config source priority order is ``pyproject.toml``, ``tox.ini`` and then ``setup.cfg`` - by :user:`gaborbernat` (`#814 <https://github.com/tox-dev/tox/issues/814>`_)
- use the os environment variable ``TOX_SKIP_ENV`` to filter out tox environment names from the run list (set by ``envlist``)  - by :user:`gaborbernat` (`#824 <https://github.com/tox-dev/tox/issues/824>`_)
- always set ``PIP_USER=0`` (do not install into the user site package, but inside the virtual environment created) and ``PIP_NO_DEPS=0`` (installing without dependencies can cause broken package installations) inside tox - by :user:`gaborbernat` (`#838 <https://github.com/tox-dev/tox/issues/838>`_)
- tox will inject some environment variables that to indicate a command is running within tox: ``TOX_WORK_DIR`` env var is set to the tox work directory,
  ``TOX_ENV_NAME`` is set to the current running tox environment name, ``TOX_ENV_DIR`` is set to the current tox environments working dir - by :user:`gaborbernat` (`#847 <https://github.com/tox-dev/tox/issues/847>`_)
- While running tox invokes various commands (such as building the package, pip installing dependencies and so on), these were printed in case they failed as Python arrays. Changed the representation to a shell command, allowing the users to quickly replicate/debug the failure on their own - by :user:`gaborbernat` (`#851 <https://github.com/tox-dev/tox/issues/851>`_)
- skip missing interpreters value from the config file can now be overridden via the ``--skip-missing-interpreters`` cli flag - by :user:`gaborbernat` (`#903 <https://github.com/tox-dev/tox/issues/903>`_)
- keep additional environments config order when listing them - by :user:`gaborbernat` (`#921 <https://github.com/tox-dev/tox/issues/921>`_)
- allow injecting config value inside the ini file dependent of the fact that we're connected to an interactive shell or not via exposing a ``{tty}`` substitution - by :user:`gaborbernat` (`#947 <https://github.com/tox-dev/tox/issues/947>`_)
- do not build sdist if skip install is specified for the envs to be run - by :user:`gaborbernat` (`#974 <https://github.com/tox-dev/tox/issues/974>`_)
- when verbosity level increases above two start passing through verbosity flags to pip - by :user:`gaborbernat` (`#982 <https://github.com/tox-dev/tox/issues/982>`_)
- when discovering the interpreter to use check if the tox host Python matches and use that if so - by :user:`gaborbernat` (`#994 <https://github.com/tox-dev/tox/issues/994>`_)
- ``-vv`` will print out why a virtual environment is re-created whenever this operation is triggered - by :user:`gaborbernat` (`#1004 <https://github.com/tox-dev/tox/issues/1004>`_)


Documentation
^^^^^^^^^^^^^

- clarify that ``python`` and ``pip`` refer to the virtual environments executable - by :user:`gaborbernat` (`#305 <https://github.com/tox-dev/tox/issues/305>`_)
- add Sphinx and mkdocs example of generating documentation via tox - by :user:`gaborbernat` (`#374 <https://github.com/tox-dev/tox/issues/374>`_)
- specify that ``setup.cfg`` tox configuration needs to be inside the ``tox:tox`` namespace - by :user:`gaborbernat` (`#545 <https://github.com/tox-dev/tox/issues/545>`_)


v3.3.0 (2018-09-11)
-------------------

Bugfixes
^^^^^^^^

- fix ``TOX_LIMITED_SHEBANG`` when running under python3 - by :user:`asottile` (`#931 <https://github.com/tox-dev/tox/issues/931>`_)


Features
^^^^^^^^

- `PEP-517 <https://www.python.org/dev/peps/pep-0517/>`_ source distribution support (create a
  ``.package`` virtual environment to perform build operations inside) by :user:`gaborbernat` (`#573 <https://github.com/tox-dev/tox/issues/573>`_)
- `flit <https://flit.readthedocs.io>`_ support via implementing ``PEP-517`` by :user:`gaborbernat` (`#820 <https://github.com/tox-dev/tox/issues/820>`_)
- packaging now is exposed as a hook via ``tox_package(session, venv)`` - by :user:`gaborbernat` (`#951 <https://github.com/tox-dev/tox/issues/951>`_)


Miscellaneous
^^^^^^^^^^^^^

- Updated the VSTS build YAML to use the latest jobs and pools syntax - by :user:`davidstaheli` (`#955 <https://github.com/tox-dev/tox/issues/955>`_)


v3.2.1 (2018-08-10)
-------------------

Bugfixes
^^^^^^^^

- ``--parallel--safe-build`` no longer cleans up its folders (``distdir``, ``distshare``, ``log``). - by :user:`gaborbernat` (`#849 <https://github.com/tox-dev/tox/issues/849>`_)


v3.2.0 (2018-08-10)
-------------------

Features
^^^^^^^^

- Switch pip invocations to use the module ``-m pip`` instead of direct invocation. This could help
  avoid some of the shebang limitations.  - by :user:`gaborbernat` (`#935 <https://github.com/tox-dev/tox/issues/935>`_)
- Ability to specify package requirements for the tox run via the ``tox.ini`` (``tox`` section under key ``requires`` - PEP-508 style): can be used to specify both plugin requirements or build dependencies. - by :user:`gaborbernat` (`#783 <https://github.com/tox-dev/tox/issues/783>`_)
- Allow one to run multiple tox instances in parallel by providing the
  ``--parallel--safe-build`` flag. - by :user:`gaborbernat` (`#849 <https://github.com/tox-dev/tox/issues/849>`_)


v3.1.3 (2018-08-03)
-------------------

Bugfixes
^^^^^^^^

- A caching issue that caused the ``develop-inst-nodeps`` action, which
  reinstalls the package under test, to always run has been resolved. The
  ``develop-inst-noop`` action, which, as the name suggests, is a no-op, will now
  run unless there are changes to ``setup.py`` or ``setup.cfg`` files that have
  not been reflected - by @stephenfin (`#909 <https://github.com/tox-dev/tox/issues/909>`_)


Features
^^^^^^^^

- Python version testenvs are now automatically detected instead of comparing
  against a hard-coded list of supported versions.  This enables ``py38`` and
  eventually ``py39`` / ``py40`` / etc. to work without requiring an upgrade to
  ``tox``.  As such, the following public constants are now deprecated
  (and scheduled for removal in ``tox`` 4.0: ``CPYTHON_VERSION_TUPLES``,
  ``PYPY_VERSION_TUPLES``, ``OTHER_PYTHON_INTERPRETERS``, and ``DEFAULT_FACTORS`` -
  by :user:`asottile` (`#914 <https://github.com/tox-dev/tox/issues/914>`_)


Documentation
^^^^^^^^^^^^^

- Add a system overview section on the index page that explains briefly how tox works -
  by :user:`gaborbernat`. (`#867 <https://github.com/tox-dev/tox/issues/867>`_)


v3.1.2 (2018-07-12)
-------------------

Bugfixes
^^^^^^^^

- Revert "Fix bug with incorrectly defactorized dependencies (`#772 <https://github.com/tox-dev/tox/issues/772>`_)" due to a regression (`(#799) <https://github.com/tox-dev/tox/issues/899>`_) - by :user:`obestwalter`

v3.1.1 (2018-07-09)
-------------------

Bugfixes
^^^^^^^^

- PyPI documentation for ``3.1.0`` is broken. Added test to check for this, and
  fix it by :user:`gaborbernat`. (`#879
  <https://github.com/tox-dev/tox/issues/879>`_)


v3.1.0 (2018-07-08)
-------------------

Bugfixes
^^^^^^^^

- Add ``ignore_basepython_conflict``, which determines whether conflicting
  ``basepython`` settings for environments containing default factors, such as
  ``py27`` or ``django18-py35``, should be ignored or result in warnings. This
  was a common source of misconfiguration and is rarely, if ever, desirable from
  a user perspective - by :user:`stephenfin` (`#477 <https://github.com/tox-dev/tox/issues/477>`_)
- Fix bug with incorrectly defactorized dependencies (deps passed to pip were not de-factorized) - by :user:`bartsanchez` (`#706 <https://github.com/tox-dev/tox/issues/706>`_)


Features
^^^^^^^^

- Add support for multiple PyPy versions using default factors. This allows you
  to use, for example, ``pypy27`` knowing that the correct interpreter will be
  used by default - by :user:`stephenfin` (`#19 <https://github.com/tox-dev/tox/issues/19>`_)
- Add support to explicitly invoke interpreter directives for environments with
  long path lengths. In the event that ``tox`` cannot invoke scripts with a
  system-limited shebang (e.x. a Linux host running a Jenkins Pipeline), a user
  can set the environment variable ``TOX_LIMITED_SHEBANG`` to workaround the
  system's limitation (e.x. ``export TOX_LIMITED_SHEBANG=1``) - by :user:`jdknight` (`#794 <https://github.com/tox-dev/tox/issues/794>`_)
- introduce a constants module to be used internally and as experimental API - by :user:`obestwalter` (`#798 <https://github.com/tox-dev/tox/issues/798>`_)
- Make ``py2`` and ``py3`` aliases also resolve via ``py`` on windows by :user:`asottile`. This enables the following things:
  ``tox -e py2`` and ``tox -e py3`` work on windows (they already work on posix); and setting ``basepython=python2`` or ``basepython=python3`` now works on windows. (`#856 <https://github.com/tox-dev/tox/issues/856>`_)
- Replace the internal version parsing logic from the not well tested `PEP-386 <https://www.python.org/dev/peps/pep-0386/>`_ parser for the more general `PEP-440 <https://www.python.org/dev/peps/pep-0440/>`_. `packaging >= 17.1 <https://pypi.org/project/packaging/>`_ is now an install dependency by :user:`gaborbernat`. (`#860 <https://github.com/tox-dev/tox/issues/860>`_)


Documentation
^^^^^^^^^^^^^

- extend the plugin documentation and make lot of small fixes and improvements - by :user:`obestwalter` (`#797 <https://github.com/tox-dev/tox/issues/797>`_)
- tidy up tests - remove unused fixtures, update old cinstructs, etc. - by :user:`obestwalter` (`#799 <https://github.com/tox-dev/tox/issues/799>`_)
- Various improvements to documentation: open browser once documentation generation is done, show Github/Travis info on documentation page, remove duplicate header for changelog, generate unreleased news as DRAFT on top of changelog, make the changelog page more compact and readable (width up to 1280px) by :user:`gaborbernat` (`#859 <https://github.com/tox-dev/tox/issues/859>`_)


Miscellaneous
^^^^^^^^^^^^^

- filter out unwanted files in package - by :user:`obestwalter` (`#754 <https://github.com/tox-dev/tox/issues/754>`_)
- make the already existing implicit API explicit - by :user:`obestwalter` (`#800 <https://github.com/tox-dev/tox/issues/800>`_)
- improve tox quickstart and corresponding tests - by :user:`obestwalter` (`#801 <https://github.com/tox-dev/tox/issues/801>`_)
- tweak codecov settings via .codecov.yml - by :user:`obestwalter` (`#802 <https://github.com/tox-dev/tox/issues/802>`_)


v3.0.0 (2018-04-02)
-------------------

Bugfixes
^^^^^^^^

- Write directly to stdout buffer if possible to prevent str vs bytes issues -
  by @asottile (`#426 <https://github.com/tox-dev/tox/issues/426>`_)
- fix #672 reporting to json file when skip-missing-interpreters option is used
  - by @r2dan (`#672 <https://github.com/tox-dev/tox/issues/672>`_)
- avoid ``Requested Python version (X.Y) not installed`` stderr output when a
  Python environment is looked up using the ``py`` Python launcher on Windows
  and the environment is not found installed on the system - by
  @jurko-gospodnetic (`#692 <https://github.com/tox-dev/tox/issues/692>`_)
- Fixed an issue where invocation of tox from the Python package, where
  invocation errors (failed actions) occur results in a change in the
  sys.stdout stream encoding in Python 3.x. New behaviour is that sys.stdout is
  reset back to its original encoding after invocation errors - by @tonybaloney
  (`#723 <https://github.com/tox-dev/tox/issues/723>`_)
- The reading of command output sometimes failed with ``IOError: [Errno 0]
  Error`` on Windows, this was fixed by using a simpler method to update the
  read buffers. - by @fschulze (`#727
  <https://github.com/tox-dev/tox/issues/727>`_)
- (only affected rc releases) fix up tox.cmdline to be callable without args - by
  @gaborbernat. (`#773 <https://github.com/tox-dev/tox/issues/773>`_)
- (only affected rc releases) Revert breaking change of tox.cmdline not callable
  with no args - by @gaborbernat. (`#773 <https://github.com/tox-dev/tox/issues/773>`_)
- (only affected rc releases) fix #755 by reverting the ``cmdline`` import to the old
  location and changing the entry point instead - by @fschulze
  (`#755 <https://github.com/tox-dev/tox/issues/755>`_)


Features
^^^^^^^^

- ``tox`` displays exit code together with ``InvocationError`` - by @blueyed
  and @ederag. (`#290 <https://github.com/tox-dev/tox/issues/290>`_)
- Hint for possible signal upon ``InvocationError``, on posix systems - by
  @ederag and @asottile. (`#766 <https://github.com/tox-dev/tox/issues/766>`_)
- Add a ``-q`` option to progressively silence tox's output. For each time you
  specify ``-q`` to tox, the output provided by tox reduces. This option allows
  you to see only your command output without the default verbosity of what tox
  is doing. This also counter-acts usage of ``-v``. For example, running ``tox
  -v -q ...`` will provide you with the default verbosity. ``tox -vv -q`` is
  equivalent to ``tox -v``. By @sigmavirus24 (`#256
  <https://github.com/tox-dev/tox/issues/256>`_)
- add support for negated factor conditions, e.g. ``!dev: production_log`` - by
  @jurko-gospodnetic (`#292 <https://github.com/tox-dev/tox/issues/292>`_)
- Headings like ``installed: <packages>`` will not be printed if there is no
  output to display after the :, unless verbosity is set. By @cryvate (`#601
  <https://github.com/tox-dev/tox/issues/601>`_)
- Allow spaces in command line options to pip in deps. Where previously only
  ``deps=-rreq.txt`` and ``deps=--requirement=req.txt`` worked, now also
  ``deps=-r req.txt`` and ``deps=--requirement req.txt`` work - by @cryvate
  (`#668 <https://github.com/tox-dev/tox/issues/668>`_)
- drop Python ``2.6`` and ``3.3`` support: ``setuptools`` dropped supporting
  these, and as we depend on it we'll follow up with doing the same (use ``tox
  <= 2.9.1`` if you still need this support) - by @gaborbernat (`#679
  <https://github.com/tox-dev/tox/issues/679>`_)
- Add tox_runenvreport as a possible plugin, allowing the overriding of the
  default behaviour to execute a command to get the installed packages within a
  virtual environment - by @tonybaloney (`#725
  <https://github.com/tox-dev/tox/issues/725>`_)
- Forward ``PROCESSOR_ARCHITECTURE`` by default on Windows to fix
  ``platform.machine()``. (`#740 <https://github.com/tox-dev/tox/issues/740>`_)


Documentation
^^^^^^^^^^^^^

- Change favicon to the vector beach ball - by @hazalozturk
  (`#748 <https://github.com/tox-dev/tox/issues/748>`_)
- Change sphinx theme to alabaster and add logo/favicon - by @hazalozturk
  (`#639 <https://github.com/tox-dev/tox/issues/639>`_)


Miscellaneous
^^^^^^^^^^^^^

- Running ``tox`` without a ``setup.py`` now has a more friendly error message
  and gives troubleshooting suggestions - by @Volcyy.
  (`#331 <https://github.com/tox-dev/tox/issues/331>`_)
- Fix pycodestyle (formerly pep8) errors E741 (ambiguous variable names, in
  this case, 'l's) and remove ignore of this error in tox.ini - by @cryvate
  (`#663 <https://github.com/tox-dev/tox/issues/663>`_)
- touched up ``interpreters.py`` code and added some missing tests for it - by
  @jurko-gospodnetic (`#708 <https://github.com/tox-dev/tox/issues/708>`_)
- The ``PYTHONDONTWRITEBYTECODE`` environment variable is no longer unset - by
  @stephenfin. (`#744 <https://github.com/tox-dev/tox/issues/744>`_)


v2.9.1 (2017-09-29)
-------------------

Miscellaneous
^^^^^^^^^^^^^

- integrated new release process and fixed changelog rendering for pypi.org -
  by `@obestwalter <https://github.com/obestwalter>`_.


v2.9.0 (2017-09-29)
-------------------

Features
^^^^^^^^

- ``tox --version`` now shows information about all registered plugins - by
  `@obestwalter <https://github.com/obestwalter>`_
  (`#544 <https://github.com/tox-dev/tox/issues/544>`_)


Bugfixes
^^^^^^^^

- ``skip_install`` overrides ``usedevelop`` (``usedevelop`` is an option to
  choose the installation type if the package is installed and ``skip_install``
  determines if it should be installed at all) - by `@ferdonline <https://github.com/ferdonline>`_
  (`#571 <https://github.com/tox-dev/tox/issues/571>`_)


Miscellaneous
^^^^^^^^^^^^^

- `#635 <https://github.com/tox-dev/tox/issues/635>`_ inherit from correct exception -
  by `@obestwalter <https://github.com/obestwalter>`_
  (`#635 <https://github.com/tox-dev/tox/issues/635>`_).
- spelling  and escape sequence fixes - by `@scoop <https://github.com/scoop>`_
  (`#637 <https://github.com/tox-dev/tox/issues/637>`_ and
  `#638 <https://github.com/tox-dev/tox/issues/638>`_).
- add a badge to show build status of documentation on readthedocs.io -
  by `@obestwalter <https://github.com/obestwalter>`_.


Documentation
^^^^^^^^^^^^^

- add `towncrier <https://github.com/hawkowl/towncrier>`_ to allow adding
  changelog entries with the pull requests without generating merge conflicts;
  with this release notes are now grouped into four distinct collections:
  ``Features``, ``Bugfixes``, ``Improved Documentation`` and ``Deprecations and
  Removals``. (`#614 <https://github.com/tox-dev/tox/issues/614>`_)


v2.8.2 (2017-10-09)
-------------------

- `#466 <https://github.com/tox-dev/tox/issues/466>`_: stop env var leakage if popen failed with resultjson or redirect

v2.8.1 (2017-09-04)
-------------------

- `pull request 599 <https://github.com/tox-dev/tox/pull/599>`_: fix problems with implementation of `#515 <https://github.com/tox-dev/tox/issues/515>`_.
  Substitutions from other sections were not made anymore if they were not in ``envlist``.
  Thanks to Clark Boylan (`@cboylan <https://github.com/cboylan>`_) for helping to get this fixed (`pull request 597 <https://github.com/tox-dev/tox/pull/597>`_).

v2.8.0 (2017-09-01)
--------------------

- `#276 <https://github.com/tox-dev/tox/issues/276>`_: Remove easy_install from docs (TL;DR: use pip). Thanks Martin Andrysík (`@sifuraz <https://github.com/sifuraz>`_).

- `#301 <https://github.com/tox-dev/tox/issues/301>`_: Expand nested substitutions in ``tox.ini``. Thanks `@vlaci <https://github.com/vlaci>`_. Thanks to Eli Collins
  (`@eli-collins <https://github.com/eli-collins>`_) for creating a reproducer.

- `#315 <https://github.com/tox-dev/tox/issues/315>`_: add ``--help`` and ``--version`` to helptox-quickstart. Thanks `@vlaci <https://github.com/vlaci>`_.

- `#326 <https://github.com/tox-dev/tox/issues/326>`_: Fix ``OSError`` 'Not a directory' when creating env on Jython 2.7.0. Thanks Nick Douma (`@LordGaav <https://github.com/LordGaav>`_).

- `#429 <https://github.com/tox-dev/tox/issues/429>`_: Forward ``MSYSTEM`` by default on Windows. Thanks Marius Gedminas (`@mgedmin <https://github.com/mgedmin>`_) for reporting this.

- `#449 <https://github.com/tox-dev/tox/issues/449>`_: add multi platform example to the docs. Thanks Aleks Bunin (`@sashkab <https://github.com/sashkab>`_) and `@rndr <https://github.com/rndr>`_.

- `#474 <https://github.com/tox-dev/tox/issues/474>`_: Start using setuptools_scm for tag based versioning.

- `#484 <https://github.com/tox-dev/tox/issues/484>`_: Renamed ``py.test`` to ``pytest`` throughout the project. Thanks Slam (`@3lnc <https://github.com/3lnc>`_).

- `#504 <https://github.com/tox-dev/tox/issues/504>`_: With ``-a``: do not show additional environments header if there are none. Thanks `@rndr <https://github.com/rndr>`_.

- `#515 <https://github.com/tox-dev/tox/issues/515>`_: Don't require environment variables in test environments where they are not used.
  Thanks André Caron (`@AndreLouisCaron <https://github.com/AndreLouisCaron>`_).
- `#517 <https://github.com/tox-dev/tox/issues/517>`_: Forward ``NUMBER_OF_PROCESSORS`` by default on Windows to fix ``multiprocessor.cpu_count()``.
  Thanks André Caron (`@AndreLouisCaron <https://github.com/AndreLouisCaron>`_).

- `#518 <https://github.com/tox-dev/tox/issues/518>`_: Forward ``USERPROFILE`` by default on Windows. Thanks André Caron (`@AndreLouisCaron <https://github.com/AndreLouisCaron>`_).

- `pull request 528 <https://github.com/tox-dev/tox/pull/528>`_: Fix some of the warnings displayed by pytest 3.1.0. Thanks Bruno Oliveira (`@nicoddemus <https://github.com/nicoddemus>`_).

- `pull request 547 <https://github.com/tox-dev/tox/pull/547>`_: Add regression test for `#137 <https://github.com/tox-dev/tox/issues/137>`_. Thanks Martin Andrysík (`@sifuraz <https://github.com/sifuraz>`_).

- `pull request 553 <https://github.com/tox-dev/tox/pull/553>`_: Add an XFAIL test to reproduce upstream bug `#203 <https://github.com/tox-dev/tox/issues/203>`_. Thanks
  Bartolomé Sánchez Salado (`@bartsanchez <https://github.com/bartsanchez>`_).

- `pull request 556 <https://github.com/tox-dev/tox/pull/556>`_: Report more meaningful errors on why virtualenv creation failed. Thanks `@vlaci <https://github.com/vlaci>`_.
  Also thanks to Igor Sadchenko (`@igor-sadchenko <https://github.com/igor-sadchenko>`_) for pointing out a problem with that PR
  before it hit the masses ☺

- `pull request 575 <https://github.com/tox-dev/tox/pull/575>`_: Add announcement doc to end all announcement docs
  (using only ``CHANGELOG`` and Github issues since 2.5 already).

- `pull request 580 <https://github.com/tox-dev/tox/pull/580>`_: Do not ignore Sphinx warnings anymore. Thanks Bernát Gábor (`@gaborbernat <https://github.com/gaborbernat>`_).

- `pull request 585 <https://github.com/tox-dev/tox/pull/585>`_: Expand documentation to explain pass through of flags from deps to pip
  (e.g. ``-rrequirements.txt``, ``-cconstraints.txt``). Thanks Alexander Loechel (`@loechel <https://github.com/loechel>`_).

- `pull request 588 <https://github.com/tox-dev/tox/pull/588>`_: Run pytest with xfail_strict and adapt affected tests.

v2.7.0 (2017-04-02)
-------------------

- `pull request 450 <https://github.com/tox-dev/tox/pull/450>`_: Stop after the first installdeps and first testenv create hooks
  succeed. This changes the default behaviour of ``tox_testenv_create`` and ``tox_testenv_install_deps`` to not execute other registered hooks when the first hook returns a result that is not ``None``.
  Thanks Anthony Sottile (`@asottile <https://github.com/asottile>`_).

- `#271 <https://github.com/tox-dev/tox/issues/271>`_ and `#464 <https://github.com/tox-dev/tox/issues/464>`_:
  Improve environment information for users.

  New command line parameter: ``-a`` show **all** defined environments -
  not just the ones defined in (or generated from) envlist.

  New verbosity settings for ``-l`` and ``-a``: show user defined descriptions
  of the environments. This also works for generated environments from factors
  by concatenating factor descriptions into a complete description.

  Note that for backwards compatibility with scripts using the output of ``-l``
  it's output remains unchanged.

  Thanks Bernát Gábor (`@gaborbernat <https://github.com/gaborbernat>`_).

- `#464 <https://github.com/tox-dev/tox/issues/464>`_: Fix incorrect egg-info location for modified package_dir in setup.py.
  Thanks Selim Belhaouane (`@selimb <https://github.com/selimb>`_).

- `#431 <https://github.com/tox-dev/tox/issues/431>`_: Add 'LANGUAGE' to default passed environment variables.
  Thanks Paweł Adamczak (`@pawelad <https://github.com/pawelad>`_).

- `#455 <https://github.com/tox-dev/tox/issues/455>`_: Add a Vagrantfile with a customized Arch Linux box for local testing.
  Thanks Oliver Bestwalter (`@obestwalter <https://github.com/obestwalter>`_).

- `#454 <https://github.com/tox-dev/tox/issues/454>`_: Revert `pull request 407 <https://github.com/tox-dev/tox/pull/407>`_, empty commands is not treated as an error.
  Thanks Anthony Sottile (`@asottile <https://github.com/asottile>`_).

- `#446 <https://github.com/tox-dev/tox/issues/446>`_: (infrastructure) Travis CI tests for tox now also run on OS X now.
  Thanks Jason R. Coombs (`@jaraco <https://github.com/jaraco>`_).

v2.6.0 (2017-02-04)
-------------------

- add "alwayscopy" config option to instruct virtualenv to always copy
  files instead of symlinking. Thanks Igor Duarte Cardoso (`@igordcard <https://github.com/igordcard>`_).

- pass setenv variables to setup.py during a usedevelop install.
  Thanks Eli Collins (`@eli-collins <https://github.com/eli-collins>`_).

- replace all references to testrun.org with readthedocs ones.
  Thanks Oliver Bestwalter (`@obestwalter <https://github.com/obestwalter>`_).

- fix `#323 <https://github.com/tox-dev/tox/issues/323>`_ by avoiding virtualenv14 is not used on py32
  (although we don't officially support py32).
  Thanks Jason R. Coombs (`@jaraco <https://github.com/jaraco>`_).

- add Python 3.6 to envlist and CI.
  Thanks Andrii Soldatenko (`@andriisoldatenko <https://github.com/andriisoldatenko>`_).

- fix glob resolution from TOX_TESTENV_PASSENV env variable
  Thanks Allan Feldman (`@a-feld <https://github.com/a-feld>`_).

v2.5.0 (2016-11-16)
-------------------

- slightly backward incompatible: fix `#310 <https://github.com/tox-dev/tox/issues/310>`_: the {posargs} substitution
  now properly preserves the tox command line positional arguments. Positional
  arguments with spaces are now properly handled.
  NOTE: if your tox invocation previously used extra quoting for positional arguments to
  work around `#310 <https://github.com/tox-dev/tox/issues/310>`_, you need to remove the quoting. Example:
  tox -- "'some string'"  # has to now be written simply as
  tox -- "some string"
  thanks holger krekel.  You can set ``minversion = 2.5.0`` in the ``[tox]``
  section of ``tox.ini`` to make sure people using your tox.ini use the correct version.

- fix `#359 <https://github.com/tox-dev/tox/issues/359>`_: add COMSPEC to default passenv on windows.  Thanks
  `@anthrotype <https://github.com/anthrotype>`_.

- add support for py36 and py37 and add py36-dev and py37(nightly) to
  travis builds of tox. Thanks John Vandenberg.

- fix `#348 <https://github.com/tox-dev/tox/issues/348>`_: add py2 and py3 as default environments pointing to
  "python2" and "python3" basepython executables.  Also fix `#347 <https://github.com/tox-dev/tox/issues/347>`_ by
  updating the list of default envs in the tox basic example.
  Thanks Tobias McNulty.

- make "-h" and "--help-ini" options work even if there is no tox.ini,
  thanks holger krekel.

- add {:} substitution, which is replaced with os-specific path
  separator, thanks Lukasz Rogalski.

- fix `#305 <https://github.com/tox-dev/tox/issues/305>`_: ``downloadcache`` test env config is now ignored as pip-8
  does caching by default. Thanks holger krekel.

- output from install command in verbose (-vv) mode is now printed to console instead of
  being redirected to file, thanks Lukasz Rogalski

- fix `#399 <https://github.com/tox-dev/tox/issues/399>`_.  Make sure {envtmpdir} is created if it doesn't exist at the
  start of a testenvironment run. Thanks Manuel Jacob.

- fix `#316 <https://github.com/tox-dev/tox/issues/316>`_: Lack of commands key in ini file is now treated as an error.
  Reported virtualenv status is 'nothing to do' instead of 'commands
  succeeded', with relevant error message displayed. Thanks Lukasz Rogalski.

v2.4.1 (2016-10-12)
-------------------

- fix `#380 <https://github.com/tox-dev/tox/issues/380>`_: properly perform substitution again. Thanks Ian
  Cordasco.

v2.4.0 (2016-10-12)
-------------------

- remove PYTHONPATH from environment during the install phase because a
  tox-run should not have hidden dependencies and the test commands will also
  not see a PYTHONPATH.  If this causes unforeseen problems it may be
  reverted in a bugfix release.  Thanks Jason R. Coombs.

- fix `#352 <https://github.com/tox-dev/tox/issues/352>`_: prevent a configuration where envdir==toxinidir and
  refine docs to warn people about changing "envdir". Thanks Oliver Bestwalter and holger krekel.

- fix `#375 <https://github.com/tox-dev/tox/issues/375>`_, fix `#330 <https://github.com/tox-dev/tox/issues/330>`_: warn against tox-setup.py integration as
  "setup.py test" should really just test with the current interpreter. Thanks Ronny Pfannschmidt.

- fix `#302 <https://github.com/tox-dev/tox/issues/302>`_: allow cross-testenv substitution where we substitute
  with ``{x,y}`` generative syntax.  Thanks Andrew Pashkin.

- fix `#212 <https://github.com/tox-dev/tox/issues/212>`_: allow escaping curly brace chars "\{" and "\}" if you need the
  chars "{" and "}" to appear in your commands or other ini values.
  Thanks John Vandenberg.

- addresses `#66 <https://github.com/tox-dev/tox/issues/66>`_: add --workdir option to override where tox stores its ".tox" directory
  and all of the virtualenv environment.  Thanks Danring.

- introduce per-venv list_dependencies_command which defaults
  to "pip freeze" to obtain the list of installed packages.
  Thanks Ted Shaw, Holger Krekel.

- close `#66 <https://github.com/tox-dev/tox/issues/66>`_: add documentation to jenkins page on how to avoid
  "too long shebang" lines when calling pip from tox.  Note that we
  can not use "python -m pip install X" by default because the latter
  adds the CWD and pip will think X is installed if it is there.
  "pip install X" does not do that.

- new list_dependencies_command to influence how tox determines
  which dependencies are installed in a testenv.

- (experimental) New feature: When a search for a config file fails, tox tries loading
  setup.cfg with a section prefix of "tox".

- fix `#275 <https://github.com/tox-dev/tox/issues/275>`_: Introduce hooks ``tox_runtest_pre``` and
  ``tox_runtest_post`` which run before and after the tests of a venv,
  respectively. Thanks to Matthew Schinckel and itxaka serrano.

- fix `#317 <https://github.com/tox-dev/tox/issues/317>`_: evaluate minversion before tox config is parsed completely.
  Thanks Sachi King for the PR.

- added the "extras" environment option to specify the extras to use when doing the
  sdist or develop install. Contributed by Alex Grönholm.

- use pytest-catchlog instead of pytest-capturelog (latter is not
  maintained, uses deprecated pytest API)

v2.3.2 (2016-02-11)
-------------------

- fix `#314 <https://github.com/tox-dev/tox/issues/314>`_: fix command invocation with .py scripts on windows.

- fix `#279 <https://github.com/tox-dev/tox/issues/279>`_: allow cross-section substitution when the value contains
  posargs. Thanks Sachi King for the PR.

v2.3.1 (2015-12-14)
-------------------

- fix `#294 <https://github.com/tox-dev/tox/issues/294>`_: re-allow cross-section substitution for setenv.

v2.3.0 (2015-12-09)
-------------------

- DEPRECATE use of "indexservers" in tox.ini.  It complicates
  the internal code and it is recommended to rather use the
  devpi system for managing indexes for pip.

- fix `#285 <https://github.com/tox-dev/tox/issues/285>`_: make setenv processing fully lazy to fix regressions
  of tox-2.2.X and so that we can now have testenv attributes like
  "basepython" depend on environment variables that are set in
  a setenv section. Thanks Nelfin for some tests and initial
  work on a PR.

- allow "#" in commands.  This is slightly incompatible with commands
  sections that used a comment after a "\" line continuation.
  Thanks David Stanek for the PR.

- fix `#289 <https://github.com/tox-dev/tox/issues/289>`_: fix build_sphinx target, thanks Barry Warsaw.

- fix `#252 <https://github.com/tox-dev/tox/issues/252>`_: allow environment names with special characters.
  Thanks Julien Castets for initial PR and patience.

- introduce experimental tox_testenv_create(venv, action) and
  tox_testenv_install_deps(venv, action) hooks to allow
  plugins to do additional work on creation or installing
  deps.  These hooks are experimental mainly because of
  the involved "venv" and session objects whose current public
  API is not fully guaranteed.

- internal: push some optional object creation into tests because
  tox core doesn't need it.

v2.2.1 (2015-12-09)
-------------------

- fix bug where {envdir} substitution could not be used in setenv
  if that env value is then used in {basepython}. Thanks Florian Bruhin.

v2.2.0 (2015-11-11)
-------------------

- fix `#265 <https://github.com/tox-dev/tox/issues/265>`_ and add LD_LIBRARY_PATH to passenv on linux by default
  because otherwise the python interpreter might not start up in
  certain configurations (redhat software collections).  Thanks David Riddle.

- fix `#246 <https://github.com/tox-dev/tox/issues/246>`_: fix regression in config parsing by reordering
  such that {envbindir} can be used again in tox.ini. Thanks Olli Walsh.

- fix `#99 <https://github.com/tox-dev/tox/issues/99>`_: the {env:...} substitution now properly uses environment
  settings from the ``setenv`` section. Thanks Itxaka Serrano.

- fix `#281 <https://github.com/tox-dev/tox/issues/281>`_: make --force-dep work when urls are present in
  dependency configs.  Thanks Glyph Lefkowitz for reporting.

- fix `#174 <https://github.com/tox-dev/tox/issues/174>`_: add new ``ignore_outcome`` testenv attribute which
  can be set to True in which case it will produce a warning instead
  of an error on a failed testenv command outcome.
  Thanks Rebecka Gulliksson for the PR.

- fix `#280 <https://github.com/tox-dev/tox/issues/280>`_: properly skip missing interpreter if
  {envsitepackagesdir} is present in commands. Thanks BB:ceridwenv


v2.1.1 (2015-06-23)
-------------------

- fix platform skipping for detox

- report skipped platforms as skips in the summary

v2.1.0 (2015-06-19)
-------------------

- fix `#258 <https://github.com/tox-dev/tox/issues/258>`_, fix `#248 <https://github.com/tox-dev/tox/issues/248>`_, fix `#253 <https://github.com/tox-dev/tox/issues/253>`_: for non-test commands
  (installation, venv creation) we pass in the full invocation environment.

- remove experimental --set-home option which was hardly used and
  hackily implemented (if people want home-directory isolation we should
  figure out a better way to do it, possibly through a plugin)

- fix `#259 <https://github.com/tox-dev/tox/issues/259>`_: passenv is now a line-list which allows interspersing
  comments.  Thanks stefano-m.

- allow envlist to be a multi-line list, to intersperse comments
  and have long envlist settings split more naturally.  Thanks Andre Caron.

- introduce a TOX_TESTENV_PASSENV setting which is honored
  when constructing the set of environment variables for test environments.
  Thanks Marc Abramowitz for pushing in this direction.

v2.0.2 (2015-06-03)
-------------------

- fix `#247 <https://github.com/tox-dev/tox/issues/247>`_: tox now passes the LANG variable from the tox invocation
  environment to the test environment by default.

- add SYSTEMDRIVE into default passenv on windows to allow pip6 to work.
  Thanks Michael Krause.

v2.0.1 (2015-05-13)
-------------------

- fix wheel packaging to properly require argparse on py26.

v2.0.0 (2015-05-12)
-------------------

- (new) introduce environment variable isolation:
  tox now only passes the PATH and PIP_INDEX_URL variable from the tox
  invocation environment to the test environment and on Windows
  also ``SYSTEMROOT``, ``PATHEXT``, ``TEMP`` and ``TMP`` whereas
  on unix additionally ``TMPDIR`` is passed.  If you need to pass
  through further environment variables you can use the new ``passenv`` setting,
  a space-separated list of environment variable names.  Each name
  can make use of fnmatch-style glob patterns.  All environment
  variables which exist in the tox-invocation environment will be copied
  to the test environment.

- a new ``--help-ini`` option shows all possible testenv settings and
  their defaults.

- (new) introduce a way to specify on which platform a testenvironment is to
  execute: the new per-venv "platform" setting allows one to specify
  a regular expression which is matched against sys.platform.
  If platform is set and doesn't match the platform spec in the test
  environment the test environment is ignored, no setup or tests are attempted.

- (new) add per-venv "ignore_errors" setting, which defaults to False.
   If ``True``, a non-zero exit code from one command will be ignored and
   further commands will be executed (which was the default behavior in tox <
   2.0).  If ``False`` (the default), then a non-zero exit code from one command
   will abort execution of commands for that environment.

- show and store in json the version dependency information for each venv

- remove the long-deprecated "distribute" option as it has no effect these days.

- fix `#233 <https://github.com/tox-dev/tox/issues/233>`_: avoid hanging with tox-setuptools integration example. Thanks simonb.

- fix `#120 <https://github.com/tox-dev/tox/issues/120>`_: allow substitution for the commands section.  Thanks
  Volodymyr Vitvitski.

- fix `#235 <https://github.com/tox-dev/tox/issues/235>`_: fix AttributeError with --installpkg.  Thanks
  Volodymyr Vitvitski.

- tox has now somewhat pep8 clean code, thanks to Volodymyr Vitvitski.

- fix `#240 <https://github.com/tox-dev/tox/issues/240>`_: allow one to specify empty argument list without it being
  rewritten to ".".  Thanks Daniel Hahler.

- introduce experimental (not much documented yet) plugin system
  based on pytest's externalized "pluggy" system.
  See tox/hookspecs.py for the current hooks.

- introduce parser.add_testenv_attribute() to register an ini-variable
  for testenv sections.  Can be used from plugins through the
  tox_add_option hook.

- rename internal files -- tox offers no external API except for the
  experimental plugin hooks, use tox internals at your own risk.

- DEPRECATE distshare in documentation

v1.9.2 (2015-03-23)
-------------------

- backout ability that --force-dep substitutes name/versions in
  requirement files due to various issues.
  This fixes `#228 <https://github.com/tox-dev/tox/issues/228>`_, fixes `#230 <https://github.com/tox-dev/tox/issues/230>`_, fixes `#231 <https://github.com/tox-dev/tox/issues/231>`_
  which popped up with 1.9.1.

v1.9.1 (2015-03-23)
-------------------

- use a file instead of a pipe for command output in "--result-json".
  Fixes some termination issues with python2.6.

- allow --force-dep to override dependencies in "-r" requirements
  files.  Thanks Sontek for the PR.

- fix `#227 <https://github.com/tox-dev/tox/issues/227>`_: use "-m virtualenv" instead of "-mvirtualenv" to make
  it work with pyrun.  Thanks Marc-Andre Lemburg.


v1.9.0 (2015-02-24)
-------------------

- fix `#193 <https://github.com/tox-dev/tox/issues/193>`_: Remove ``--pre`` from the default ``install_command``; by
  default tox will now only install final releases from PyPI for unpinned
  dependencies. Use ``pip_pre = true`` in a testenv or the ``--pre``
  command-line option to restore the previous behavior.

- fix `#199 <https://github.com/tox-dev/tox/issues/199>`_: fill resultlog structure ahead of virtualenv creation

- refine determination if we run from Jenkins, thanks Borge Lanes.

- echo output to stdout when ``--report-json`` is used

- fix `#11 <https://github.com/tox-dev/tox/issues/11>`_: add a ``skip_install`` per-testenv setting which
  prevents the installation of a package. Thanks Julian Krause.

- fix `#124 <https://github.com/tox-dev/tox/issues/124>`_: ignore command exit codes; when a command has a "-" prefix,
  tox will ignore the exit code of that command

- fix `#198 <https://github.com/tox-dev/tox/issues/198>`_: fix broken envlist settings, e.g. {py26,py27}{-lint,}

- fix `#191 <https://github.com/tox-dev/tox/issues/191>`_: lessen factor-use checks


v1.8.1 (2014-10-24)
-------------------

- fix `#190 <https://github.com/tox-dev/tox/issues/190>`_: allow setenv to be empty.

- allow escaping curly braces with "\".  Thanks Marc Abramowitz for the PR.

- allow "." names in environment names such that "py27-django1.7" is a
  valid environment name.  Thanks Alex Gaynor and Alex Schepanovski.

- report subprocess exit code when execution fails.  Thanks Marius
  Gedminas.

v1.8.0 (2014-09-24)
-------------------

- new multi-dimensional configuration support.  Many thanks to
  Alexander Schepanovski for the complete PR with docs.
  And to Mike Bayer and others for testing and feedback.

- fix `#148 <https://github.com/tox-dev/tox/issues/148>`_: remove "__PYVENV_LAUNCHER__" from os.environ when starting
  subprocesses. Thanks Steven Myint.

- fix `#152 <https://github.com/tox-dev/tox/issues/152>`_: set VIRTUAL_ENV when running test commands,
  thanks Florian Ludwig.

- better report if we can't get version_info from an interpreter
  executable. Thanks Floris Bruynooghe.


v1.7.2 (2014-07-15)
-------------------

- fix `#150 <https://github.com/tox-dev/tox/issues/150>`_: parse {posargs} more like we used to do it pre 1.7.0.
  The 1.7.0 behaviour broke a lot of OpenStack projects.
  See PR85 and the issue discussions for (far) more details, hopefully
  resulting in a more refined behaviour in the 1.8 series.
  And thanks to Clark Boylan for the PR.

- fix `#59 <https://github.com/tox-dev/tox/issues/59>`_: add a config variable ``skip-missing-interpreters`` as well as
  command line option ``--skip-missing-interpreters`` which won't fail the
  build if Python interpreters listed in tox.ini are missing.  Thanks
  Alexandre Conrad for PR104.

- fix `#164 <https://github.com/tox-dev/tox/issues/164>`_: better traceback info in case of failing test commands.
  Thanks Marc Abramowitz for PR92.

- support optional env variable substitution, thanks Morgan Fainberg
  for PR86.

- limit python hashseed to 1024 on Windows to prevent possible
  memory errors.  Thanks March Schlaich for the PR90.

v1.7.1 (2014-03-28)
-------------------

- fix `#162 <https://github.com/tox-dev/tox/issues/162>`_: don't list python 2.5 as compatible/supported

- fix `#158 <https://github.com/tox-dev/tox/issues/158>`_ and fix `#155 <https://github.com/tox-dev/tox/issues/155>`_: windows/virtualenv properly works now:
  call virtualenv through "python -m virtualenv" with the same
  interpreter which invoked tox.  Thanks Chris Withers, Ionel Maries Cristian.

v1.7.0 (2014-01-29)
-------------------

- don't lookup "pip-script" anymore but rather just "pip" on windows
  as this is a pip implementation detail and changed with pip-1.5.
  It might mean that tox-1.7 is not able to install a different pip
  version into a virtualenv anymore.

- drop Python2.5 compatibility because it became too hard due
  to the setuptools-2.0 dropping support.  tox now has no
  support for creating python2.5 based environments anymore
  and all internal special-handling has been removed.

- merged PR81: new option --force-dep which allows one to
  override tox.ini specified dependencies in setuptools-style.
  For example "--force-dep 'django<1.6'" will make sure
  that any environment using "django" as a dependency will
  get the latest 1.5 release.  Thanks Bruno Oliveria for
  the complete PR.

- merged PR125: tox now sets "PYTHONHASHSEED" to a random value
  and offers a "--hashseed" option to repeat a test run with a specific seed.
  You can also use --hashsheed=noset to instruct tox to leave the value
  alone.  Thanks Chris Jerdonek for all the work behind this.

- fix `#132 <https://github.com/tox-dev/tox/issues/132>`_: removing zip_safe setting (so it defaults to false)
  to allow installation of tox
  via easy_install/eggs.  Thanks Jenisys.

- fix `#126 <https://github.com/tox-dev/tox/issues/126>`_: depend on virtualenv>=1.11.2 so that we can rely
  (hopefully) on a pip version which supports --pre. (tox by default
  uses to --pre).  also merged in PR84 so that we now call "virtualenv"
  directly instead of looking up interpreters.  Thanks Ionel Maries Cristian.
  This also fixes `#140 <https://github.com/tox-dev/tox/issues/140>`_.

- fix `#130 <https://github.com/tox-dev/tox/issues/130>`_: you can now set install_command=easy_install {opts} {packages}
  and expect it to work for repeated tox runs (previously it only worked
  when always recreating).  Thanks jenisys for precise reporting.

- fix `#129 <https://github.com/tox-dev/tox/issues/129>`_: tox now uses Popen(..., universal_newlines=True) to force
  creation of unicode stdout/stderr streams.  fixes a problem on specific
  platform configs when creating virtualenvs with Python3.3. Thanks
  Jorgen Schäfer or investigation and solution sketch.

- fix `#128 <https://github.com/tox-dev/tox/issues/128>`_: enable full substitution in install_command,
  thanks for the PR to Ronald Evers

- rework and simplify "commands" parsing and in particular posargs
  substitutions to avoid various win32/posix related quoting issues.

- make sure that the --installpkg option trumps any usedevelop settings
  in tox.ini or

- introduce --no-network to tox's own test suite to skip tests
  requiring networks

- introduce --sitepackages to force sitepackages=True in all
  environments.

- fix `#105 <https://github.com/tox-dev/tox/issues/105>`_ -- don't depend on an existing HOME directory from tox tests.

v1.6.1 (2013-09-04)
-------------------

- fix `#119 <https://github.com/tox-dev/tox/issues/119>`_: {envsitepackagesdir} is now correctly computed and has
  a better test to prevent regression.

- fix `#116 <https://github.com/tox-dev/tox/issues/116>`_: make 1.6 introduced behaviour of changing to a
  per-env HOME directory during install activities dependent
  on "--set-home" for now.  Should re-establish the old behaviour
  when no option is given.

- fix `#118 <https://github.com/tox-dev/tox/issues/118>`_: correctly have two tests use realpath(). Thanks Barry
  Warsaw.

- fix test runs on environments without a home directory
  (in this case we use toxinidir as the homedir)

- fix `#117 <https://github.com/tox-dev/tox/issues/117>`_: python2.5 fix: don't use ``--insecure`` option because
  its very existence depends on presence of "ssl".  If you
  want to support python2.5/pip1.3.1 based test environments you need
  to install ssl and/or use PIP_INSECURE=1 through ``setenv``. section.

- fix `#102 <https://github.com/tox-dev/tox/issues/102>`_: change to {toxinidir} when installing dependencies.
  This allows one to use relative path like in "-rrequirements.txt".

v1.6.0 (2013-08-15)
-------------------

- fix `#35 <https://github.com/tox-dev/tox/issues/35>`_: add new EXPERIMENTAL "install_command" testenv-option to
  configure the installation command with options for dep/pkg install.
  Thanks Carl Meyer for the PR and docs.

- fix `#91 <https://github.com/tox-dev/tox/issues/91>`_: python2.5 support by vendoring the virtualenv-1.9.1
  script and forcing pip<1.4. Also the default [py25] environment
  modifies the default installer_command (new config option)
  to use pip without the "--pre" option which was introduced
  with pip-1.4 and is now required if you want to install non-stable
  releases.  (tox defaults to install with "--pre" everywhere).

- during installation of dependencies HOME is now set to a pseudo
  location ({envtmpdir}/pseudo-home).  If an index url was specified
  a .pydistutils.cfg file will be written with an index_url setting
  so that packages defining ``setup_requires`` dependencies will not
  silently use your HOME-directory settings or PyPI.

- fix `#1 <https://github.com/tox-dev/tox/issues/1>`_: empty setup files are properly detected, thanks Anthon van
  der Neuth

- remove toxbootstrap.py for now because it is broken.

- fix `#109 <https://github.com/tox-dev/tox/issues/109>`_ and fix `#111 <https://github.com/tox-dev/tox/issues/111>`_: multiple "-e" options are now combined
  (previously the last one would win). Thanks Anthon van der Neut.

- add --result-json option to write out detailed per-venv information
  into a json report file to be used by upstream tools.

- add new config options ``usedevelop`` and ``skipsdist`` as well as a
  command line option ``--develop`` to install the package-under-test in develop mode.
  thanks Monty Tailor for the PR.

- always unset PYTHONDONTWRITEBYTE because newer setuptools doesn't like it

- if a HOMEDIR cannot be determined, use the toxinidir.

- refactor interpreter information detection to live in new
  tox/interpreters.py file, tests in tests/test_interpreters.py.

v1.5.0 (2013-06-22)
-------------------

- fix `#104 <https://github.com/tox-dev/tox/issues/104>`_: use setuptools by default, instead of distribute,
  now that setuptools has distribute merged.

- make sure test commands are searched first in the virtualenv

- re-fix `#2 <https://github.com/tox-dev/tox/issues/2>`_ - add whitelist_externals to be used in ``[testenv*]``
  sections, allowing to avoid warnings for commands such as ``make``,
  used from the commands value.

- fix `#97 <https://github.com/tox-dev/tox/issues/97>`_ - allow substitutions to reference from other sections
  (thanks Krisztian Fekete)

- fix `#92 <https://github.com/tox-dev/tox/issues/92>`_ - fix {envsitepackagesdir} to actually work again

- show (test) command that is being executed, thanks
  Lukasz Balcerzak

- re-license tox to MIT license

- depend on virtualenv-1.9.1

- rename README.txt to README.rst to make bitbucket happier


v1.4.3 (2013-02-28)
-------------------

- use pip-script.py instead of pip.exe on win32 to avoid the lock exe
  file on execution issue (thanks Philip Thiem)

- introduce -l|--listenv option to list configured environments
  (thanks  Lukasz Balcerzak)

- fix downloadcache determination to work according to docs: Only
  make pip use a download cache if PIP_DOWNLOAD_CACHE or a
  downloadcache=PATH testenv setting is present. (The ENV setting
  takes precedence)

- fix `#84 <https://github.com/tox-dev/tox/issues/84>`_ - pypy on windows creates a bin not a scripts venv directory
  (thanks Lukasz Balcerzak)

- experimentally introduce --installpkg=PATH option to install a package
  rather than create/install an sdist package.  This will still require
  and use tox.ini and tests from the current working dir (and not from the
  remote package).

- substitute {envsitepackagesdir} with the package installation
  directory (closes `#72 <https://github.com/tox-dev/tox/issues/72>`_) (thanks g2p)

- issue `#70 <https://github.com/tox-dev/tox/issues/70>`_ remove PYTHONDONTWRITEBYTECODE workaround now that
  virtualenv behaves properly (thanks g2p)

- merged tox-quickstart command, contributed by Marc Abramowitz, which
  generates a default tox.ini after asking a few questions

- fix `#48 <https://github.com/tox-dev/tox/issues/48>`_ - win32 detection of pypy and other interpreters that are on PATH
  (thanks Gustavo Picon)

- fix grouping of index servers, it is now done by name instead of
  indexserver url, allowing to use it to separate dependencies
  into groups even if using the same default indexserver.

- look for "tox.ini" files in parent dirs of current dir (closes `#34 <https://github.com/tox-dev/tox/issues/34>`_)

- the "py" environment now by default uses the current interpreter
  (sys.executable) make tox' own setup.py test execute tests with it
  (closes `#46 <https://github.com/tox-dev/tox/issues/46>`_)

- change tests to not rely on os.path.expanduser (closes `#60 <https://github.com/tox-dev/tox/issues/60>`_),
  also make mock session return args[1:] for more precise checking (closes `#61 <https://github.com/tox-dev/tox/issues/61>`_)
  thanks to Barry Warsaw for both.

v1.4.2 (2012-07-20)
-------------------

- fix some tests which fail if /tmp is a symlink to some other place
- "python setup.py test" now runs tox tests via tox :)
  also added an example on how to do it for your project.

v1.4.1 (2012-07-03)
-------------------

- fix `#41 <https://github.com/tox-dev/tox/issues/41>`_ better quoting on windows - you can now use "<" and ">" in
  deps specifications, thanks Chris Withers for reporting

v1.4 (2012-06-13)
-----------------

- fix `#26 <https://github.com/tox-dev/tox/issues/26>`_ - no warnings on absolute or relative specified paths for commands
- fix `#33 <https://github.com/tox-dev/tox/issues/33>`_ - commentchars are ignored in key-value settings allowing
  for specifying commands like: python -c "import sys ; print sys"
  which would formerly raise irritating errors because the ";"
  was considered a comment
- tweak and improve reporting
- refactor reporting and virtualenv manipulation
  to be more accessible from 3rd party tools
- support value substitution from other sections
  with the {[section]key} syntax
- fix `#29 <https://github.com/tox-dev/tox/issues/29>`_ - correctly point to pytest explanation
  for importing modules fully qualified
- fix `#32 <https://github.com/tox-dev/tox/issues/32>`_ - use --system-site-packages and don't pass --no-site-packages
- add python3.3 to the default env list, so early adopters can test
- drop python2.4 support (you can still have your tests run on
- fix the links/checkout howtos in the docs
  python-2.4, just tox itself requires 2.5 or higher.

v1.3 2011-12-21
---------------

- fix: allow one to specify wildcard filesystem paths when
  specifying dependencies such that tox searches for
  the highest version

- fix issue `#21 <https://github.com/tox-dev/tox/issues/21>`_: clear PIP_REQUIRES_VIRTUALENV which avoids
  pip installing to the wrong environment, thanks to bb's streeter

- make the install step honour a testenv's setenv setting
  (thanks Ralf Schmitt)


v1.2 2011-11-10
---------------

- remove the virtualenv.py that was distributed with tox and depend
  on >=virtualenv-1.6.4 (possible now since the latter fixes a few bugs
  that the inlining tried to work around)
- fix `#10 <https://github.com/tox-dev/tox/issues/10>`_: work around UnicodeDecodeError when invoking pip (thanks
  Marc Abramowitz)
- fix a problem with parsing {posargs} in tox commands (spotted by goodwill)
- fix the warning check for commands to be installed in testenvironment
  (thanks Michael Foord for reporting)

v1.1 (2011-07-08)
-----------------

- fix `#5 <https://github.com/tox-dev/tox/issues/5>`_ - don't require argparse for python versions that have it
- fix `#6 <https://github.com/tox-dev/tox/issues/6>`_ - recreate virtualenv if installing dependencies failed
- fix `#3 <https://github.com/tox-dev/tox/issues/3>`_ - fix example on frontpage
- fix `#2 <https://github.com/tox-dev/tox/issues/2>`_ - warn if a test command does not come from the test
  environment
- fixed/enhanced: except for initial install always call "-U
  --no-deps" for installing the sdist package to ensure that a package
  gets upgraded even if its version number did not change. (reported on
  TIP mailing list and IRC)
- inline virtualenv.py (1.6.1) script to avoid a number of issues,
  particularly failing to install python3 environments from a python2
  virtualenv installation.
- rework and enhance docs for display on readthedocs.org

v1.0
----

- move repository and toxbootstrap links to https://bitbucket.org/hpk42/tox
- fix `#7 <https://github.com/tox-dev/tox/issues/7>`_: introduce a "minversion" directive such that tox
  bails out if it does not have the correct version.
- fix `#24 <https://github.com/tox-dev/tox/issues/24>`_: introduce a way to set environment variables for
  for test commands (thanks Chris Rose)
- fix `#22 <https://github.com/tox-dev/tox/issues/22>`_: require virtualenv-1.6.1, obsoleting virtualenv5 (thanks Jannis Leidel)
  and making things work with pypy-1.5 and python3 more seamlessly
- toxbootstrap.py (used by jenkins build agents) now follows the latest release of virtualenv
- fix `#20 <https://github.com/tox-dev/tox/issues/20>`_: document format of URLs for specifying dependencies
- fix `#19 <https://github.com/tox-dev/tox/issues/19>`_: substitute Hudson for Jenkins everywhere following the renaming
  of the project.  NOTE: if you used the special [tox:hudson]
  section it will now need to be named [tox:jenkins].
- fix issue 23 / apply some ReST fixes
- change the positional argument specifier to use {posargs:} syntax and
  fix issues `#15 <https://github.com/tox-dev/tox/issues/15>`_ and `#10 <https://github.com/tox-dev/tox/issues/10>`_ by refining the argument parsing method (Chris Rose)
- remove use of inipkg lazy importing logic -
  the namespace/imports are anyway very small with tox.
- fix a fspath related assertion to work with debian installs which uses
  symlinks
- show path of the underlying virtualenv invocation and bootstrap
  virtualenv.py into a working subdir
- added a CONTRIBUTORS file

v0.9
----

- fix pip-installation mixups by always unsetting PIP_RESPECT_VIRTUALENV
  (thanks Armin Ronacher)
- `#1 <https://github.com/tox-dev/tox/issues/1>`_: Add a toxbootstrap.py script for tox, thanks to Sridhar
  Ratnakumar
- added support for working with different and multiple PyPI indexservers.
- new option: -r|--recreate to force recreation of virtualenv
- depend on py>=1.4.0 which does not contain or install the py.test
  anymore which is now a separate distribution "pytest".
- show logfile content if there is an error (makes CI output
  more readable)

v0.8
----

- work around a virtualenv limitation which crashes if
  PYTHONDONTWRITEBYTECODE is set.
- run pip/easy installs from the environment log directory, avoids
  naming clashes between env names and dependencies (thanks ronny)
- require a more recent version of py lib
- refactor and refine config detection to work from a single file
  and to detect the case where a python installation overwrote
  an old one and resulted in a new executable. This invalidates
  the existing virtualenvironment now.
- change all internal source to strip trailing whitespaces

v0.7
----

- use virtualenv5 (my own fork of virtualenv3) for now to create python3
  environments, fixes a couple of issues and makes tox more likely to
  work with Python3 (on non-windows environments)

- add ``sitepackages`` option for testenv sections so that environments
  can be created with access to globals (default is not to have access,
  i.e. create environments with ``--no-site-packages``.

- addressing `#4 <https://github.com/tox-dev/tox/issues/4>`_: always prepend venv-path to PATH variable when calling subprocesses

- fix `#2 <https://github.com/tox-dev/tox/issues/2>`_: exit with proper non-zero return code if there were
  errors or test failures.

- added unittest2 examples contributed by Michael Foord

- only allow 'True' or 'False' for boolean config values
  (lowercase / uppercase is irrelevant)

- recreate virtualenv on changed configurations

v0.6
----

- fix OSX related bugs that could cause the caller's environment to get
  screwed (sorry).  tox was using the same file as virtualenv for tracking
  the Python executable dependency and there also was confusion wrt links.
  this should be fixed now.

- fix long description, thanks Michael Foord

v0.5
----

- initial release
