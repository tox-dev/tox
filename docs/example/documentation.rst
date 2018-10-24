Generate documentation
======================

It's possible to generate the projects documentation with tox itself. The advantage of this
path is that now generating the documentation can be part of the CI, and whenever any
validations/checks/operations fail while generating the documentation you'll catch it
within tox.

Sphinx
------

No need to use the cryptic make file to generate a sphinx documentation. One can use tox
to ensure all right dependencies are available within a virtual environment, and
even specify the python version needed to perform the build. For example if the sphinx
file structure is under the ``doc`` folder the following configuration will generate
the documentation under ``{toxworkdir}/docs_out`` and print out a link to the generated
documentation:

.. code-block:: ini

    [testenv:docs]
    description = invoke sphinx-build to build the HTML docs
    basepython = python3.7
    deps = sphinx >= 1.7.5, < 2
    commands = sphinx-build -d "{toxworkdir}/docs_doctree" doc "{toxworkdir}/docs_out" --color -W -bhtml {posargs}
               python -c 'import pathlib; print("documentation available under file://\{0\}".format(pathlib.Path(r"{toxworkdir}") / "docs_out" / "index.html"))'

Note here we say we also require python 3.7, allowing us to use f-strings within the sphinx
``conf.py``. Now one can specify a separate test environment that will validate that the
links are correct.

mkdocs
------

Define one environment to write/generate the documentation, and another to deploy it. Use
the config substitution logic to avoid defining dependencies multiple time:

.. code-block:: ini

    [testenv:docs]
    description = Run a development server for working on documentation
    basepython = python3.7
    deps = mkdocs >= 1.7.5, < 2
           mkdocs-material
    commands = mkdocs build --clean
               python -c 'print("###### Starting local server. Press Control+C to stop server ######")'
               mkdocs serve -a localhost:8080

    [testenv:docs-deploy]
    description = built fresh docs and deploy them
    deps = {[testenv:docs]deps}
    basepython = {[testenv:docs]basepython}
    commands = mkdocs gh-deploy --clean
