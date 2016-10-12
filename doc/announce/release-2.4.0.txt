tox-2.4.0 brings some fixes and new features, see the changelog below.  Docs are now at:

    https://tox.readthedocs.org

And thanks to Ronny Pfannschmidt the tox repository is now on github:

    https://github.com/tox-dev/tox

Also many thanks to Oliver Bestwalter, Alex Grönholm, Stefan Obermann, Danielle Jenkins, Ted Shaw, Andrzej Ostrowski and Florian Bruhin who helped with the release particularly during the testing sprint we had in June 2016.

have testing fun,
holger krekel


2.4.0
-----

- remove PYTHONPATH from environment during the install phase because a
  tox-run should not have hidden dependencies and the test commands will also
  not see a PYTHONPATH.  If this causes unforeseen problems it may be
  reverted in a bugfix release.  Thanks Jason R. Coombs.

- fix issue352: prevent a configuration where envdir==toxinidir and
  refine docs to warn people about changing "envdir". Thanks Oliver Bestwalter and holger krekel.

- fix issue375, fix issue330: warn against tox-setup.py integration as
  "setup.py test" should really just test with the current interpreter. Thanks Ronny Pfannschmidt.

- fix issue302: allow cross-testenv substitution where we substitute
  with ``{x,y}`` generative syntax.  Thanks Andrew Pashkin.

- fix issue212: allow escaping curly brace chars "\{" and "\}" if you need the
  chars "{" and "}" to appear in your commands or other ini values.
  Thanks John Vandenberg.

- addresses issue66: add --workdir option to override where tox stores its ".tox" directory
  and all of the virtualenv environment.  Thanks Danring.

- introduce per-venv list_dependencies_command which defaults
  to "pip freeze" to obtain the list of installed packages.
  Thanks Ted Shaw, Holger Krekel.

- close issue66: add documentation to jenkins page on how to avoid
  "too long shebang" lines when calling pip from tox.  Note that we
  can not use "python -m pip install X" by default because the latter
  adds the CWD and pip will think X is installed if it is there.
  "pip install X" does not do that.

- new list_dependencies_command to influence how tox determines
  which dependencies are installed in a testenv.

- (experimental) New feature: When a search for a config file fails, tox tries loading
  setup.cfg with a section prefix of "tox".

- fix issue275: Introduce hooks ``tox_runtest_pre``` and
  ``tox_runtest_post`` which run before and after the tests of a venv,
  respectively. Thanks to Matthew Schinckel and itxaka serrano.

- fix issue317: evaluate minversion before tox config is parsed completely.
  Thanks Sachi King for the PR.

- added the "extras" environment option to specify the extras to use when doing the
  sdist or develop install. Contributed by Alex Grönholm.

- use pytest-catchlog instead of pytest-capturelog (latter is not
  maintained, uses deprecated pytest API)
