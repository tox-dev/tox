Using tox with the Jenkins Integration Server
=================================================

Using Jenkins multi-configuration jobs
-------------------------------------------

The Jenkins_ continuous integration server allows you to define "jobs" with
"build steps" which can be test invocations.  If you :doc:`install <../install>` ``tox`` on your
default Python installation on each Jenkins agent, you can easily create
a Jenkins multi-configuration job that will drive your tox runs from the CI-server side,
using these steps:

* install the Python plugin for Jenkins under "manage jenkins"
* create a "multi-configuration" job, give it a name of your choice
* configure your repository so that Jenkins can pull it
* (optional) configure multiple nodes so that tox-runs are performed
  on multiple hosts
* configure ``axes`` by using :ref:`TOXENV <TOXENV>` as an axis
  name and as values provide space-separated test environment names
  you want Jenkins/tox to execute.

* add a **Python-build step** with this content (see also next example):

    .. code-block:: python

        import tox

        os.chdir(os.getenv("WORKSPACE"))
        tox.cmdline()  # environment is selected by ``TOXENV`` env variable

* check ``Publish JUnit test result report`` and enter
  ``**/junit-*.xml`` as the pattern so that Jenkins collects
  test results in the JUnit XML format.

The last point requires that your test command creates JunitXML files,
for example with ``pytest`` it is done like this:

.. code-block:: ini

    [testenv]
    commands = pytest --junitxml=junit-{envname}.xml



**zero-installation** for agents
-------------------------------------------------------------

.. note::

    This feature is broken currently because "toxbootstrap.py"
    has been removed.  Please file an issue if you'd like to
    see it back.

If you manage many Jenkins agents and want to use the latest officially
released tox (or latest development version) and want to skip manually
installing ``tox`` then substitute the above **Python build step** code
with this:

.. code-block:: python

    import urllib, os

    url = "https://bitbucket.org/hpk42/tox/raw/default/toxbootstrap.py"
    # os.environ['USETOXDEV']="1"  # use tox dev version
    d = dict(__file__="toxbootstrap.py")
    exec(urllib.urlopen(url).read(), globals=d)
    d["cmdline"](["--recreate"])

The downloaded ``toxbootstrap.py`` file downloads all necessary files to
install ``tox`` in a virtual sub environment.  Notes:

* uncomment the line containing ``USETOXDEV`` to use the latest
  development-release version of tox instead of the
  latest released version.

* adapt the options in the last line as needed (the example code
  will cause tox to reinstall all virtual environments all the time
  which is often what one wants in CI server contexts)


Integrating "sphinx" documentation checks in a Jenkins job
----------------------------------------------------------------

If you are using a multi-configuration Jenkins job which collects
JUnit Test results you will run into problems using the previous
method of running the sphinx-build command because it will not
generate JUnit results.  To accommodate this issue one solution
is to have ``pytest`` wrap the sphinx-checks and create a
JUnit result file which wraps the result of calling sphinx-build.
Here is an example:

1. create a ``docs`` environment in your ``tox.ini`` file like this:

  .. code-block:: ini

      [testenv:docs]
      basepython = python
      # change to ``doc`` dir if that is where your sphinx-docs live
      changedir = doc
      deps = sphinx
             pytest
      commands = pytest --tb=line -v --junitxml=junit-{envname}.xml check_sphinx.py

2. create a ``doc/check_sphinx.py`` file like this:

  .. code-block:: python

    import subprocess


    def test_linkcheck(tmpdir):
        doctrees = tmpdir.join("doctrees")
        htmldir = tmpdir.join("html")
        subprocess.check_call(
            ["sphinx-build", "-W", "-blinkcheck", "-d", str(doctrees), ".", str(htmldir)]
        )


    def test_build_docs(tmpdir):
        doctrees = tmpdir.join("doctrees")
        htmldir = tmpdir.join("html")
        subprocess.check_call(
            ["sphinx-build", "-W", "-bhtml", "-d", str(doctrees), ".", str(htmldir)]
        )

3. run ``tox -e docs`` and then you may integrate this environment
   along with your other environments into Jenkins.

Note that ``pytest`` is only installed into the docs environment
and does not need to be in use or installed with any other environment.

.. _`jenkins artifact example`:

Access package artifacts between Jenkins jobs
--------------------------------------------------------

.. _`Jenkins Copy Artifact plugin`: https://wiki.jenkins.io/display/JENKINS/Copy+Artifact+Plugin

In an extension to :ref:`artifacts` you can also configure Jenkins jobs to
access each others artifacts.  ``tox`` uses the ``distshare`` directory
to access artifacts and in a Jenkins context (detected via existence
of the environment variable ``HUDSON_URL``); it defaults to
to ``{toxworkdir}/distshare``.

This means that each workspace will have its own ``distshare``
directory and we need to configure Jenkins to perform artifact copying.
The recommend way to do this is to install the `Jenkins Copy Artifact plugin`_
and for each job which "receives" artifacts you add a **Copy artifacts from another project** build step
using roughly this configuration:


  .. code-block:: shell

    Project-name: name of the other (tox-managed) job you want the artifact from
    Artifacts to copy: .tox/dist/*.zip   # where tox jobs create artifacts
    Target directory: .tox/distshare     # where we want it to appear for us
    Flatten Directories: CHECK           # create no subdir-structure

You also need to configure the "other" job to archive artifacts; This
is done by checking ``Archive the artifacts`` and entering:

  .. code-block:: shell

    Files to archive: .tox/dist/*.zip

So our "other" job will create an sdist-package artifact and
the "copy-artifacts" plugin will copy it to our ``distshare`` area.
Now everything proceeds as :ref:`artifacts` shows it.

So if you are using defaults you can re-use and debug exactly the
same ``tox.ini`` file and make use of automatic sharing of
your artifacts between runs or Jenkins jobs.


Avoiding the "path too long" error with long shebang lines
---------------------------------------------------------------

When using ``tox`` on a Jenkins instance, there may be a scenario where ``tox``
can not invoke ``pip`` because the shebang (Unix) line is too long. Some systems
only support a limited amount of characters for an interpreter directive (e.x.
Linux as a limit of 128). There are two methods to workaround this issue:

 1. Invoke ``tox`` with the ``--workdir`` option which tells ``tox`` to use a
    specific directory for its virtual environments. Using a unique and short
    path can prevent this issue.
 2. Use the environment variable ``TOX_LIMITED_SHEBANG`` to deal with
    environments with interpreter directive limitations (consult
    :ref:`long interpreter directives` for more information).


Running tox environments in parallel
------------------------------------

Jenkins has parallel stages allowing you to run commands in parallel, however tox package
building it is not parallel safe. Use the ``--parallel--safe-build`` flag to enable parallel safe
builds (this will generate unique folder names for ``distdir``, ``distshare`` and ``log``.
Here's a generic stage definition demonstrating how to use this inside Jenkins:

.. code-block:: groovy

    stage('run tox envs') {
      steps {
        script {
          def envs = sh(returnStdout: true, script: "tox -l").trim().split('\n')
          def cmds = envs.collectEntries({ tox_env ->
            [tox_env, {
              sh "tox --parallel--safe-build -vve $tox_env"
            }]
          })
          parallel(cmds)
        }
      }
    }

.. include:: ../links.rst
