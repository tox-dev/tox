import json
import textwrap
from collections import namedtuple

import pkg_resources
import six

from tox.config import DepConfig, get_py_project_toml

BuildInfo = namedtuple("BuildInfo", ["requires", "backend_module", "backend_object"])


def build(config, report, session):
    build_info = get_build_info(config.setupdir, report)
    package_venv = session.getvenv(config.isolated_build_env)
    package_venv.envconfig.deps_matches_subset = True

    # we allow user specified dependencies so the users can write extensions to
    # install additional type of dependencies (e.g. binary)
    user_specified_deps = package_venv.envconfig.deps
    package_venv.envconfig.deps = [DepConfig(r, None) for r in build_info.requires]
    package_venv.envconfig.deps.extend(user_specified_deps)

    if session.setupenv(package_venv):
        session.finishvenv(package_venv)

    build_requires = get_build_requires(build_info, package_venv, session)
    # we need to filter out requirements already specified in pyproject.toml or user deps
    base_build_deps = {pkg_resources.Requirement(r.name).key for r in package_venv.envconfig.deps}
    build_requires_dep = [
        DepConfig(r, None)
        for r in build_requires
        if pkg_resources.Requirement(r).key not in base_build_deps
    ]
    if build_requires_dep:
        with session.newaction(
            package_venv, "build_requires", package_venv.envconfig.envdir
        ) as action:
            package_venv.run_install_command(packages=build_requires_dep, action=action)
        session.finishvenv(package_venv)
    return perform_isolated_build(build_info, package_venv, session, config, report)


def get_build_info(folder, report):
    toml_file = folder.join("pyproject.toml")

    # as per https://www.python.org/dev/peps/pep-0517/

    def abort(message):
        report.error("{} inside {}".format(message, toml_file))
        raise SystemExit(1)

    if not toml_file.exists():
        report.error("missing {}".format(toml_file))
        raise SystemExit(1)

    config_data = get_py_project_toml(toml_file)

    if "build-system" not in config_data:
        abort("build-system section missing")

    build_system = config_data["build-system"]

    if "requires" not in build_system:
        abort("missing requires key at build-system section")
    if "build-backend" not in build_system:
        abort("missing build-backend key at build-system section")

    requires = build_system["requires"]
    if not isinstance(requires, list) or not all(isinstance(i, six.text_type) for i in requires):
        abort("requires key at build-system section must be a list of string")

    backend = build_system["build-backend"]
    if not isinstance(backend, six.text_type):
        abort("build-backend key at build-system section must be a string")

    args = backend.split(":")
    module = args[0]
    obj = "" if len(args) == 1 else ".{}".format(args[1])

    return BuildInfo(requires, module, "{}{}".format(module, obj))


def perform_isolated_build(build_info, package_venv, session, config, report):
    with session.newaction(
        package_venv, "perform-isolated-build", package_venv.envconfig.envdir
    ) as action:
        script = textwrap.dedent(
            """
            import sys
            import {}
            basename = {}.build_{}({!r}, {{ "--global-option": ["--formats=gztar"]}})
            print(basename)""".format(
                build_info.backend_module, build_info.backend_object, "sdist", str(config.distdir)
            )
        )

        # need to start with an empty (but existing) source distribution folder
        if config.distdir.exists():
            config.distdir.remove(rec=1, ignore_errors=True)
        config.distdir.ensure_dir()

        result = package_venv._pcall(
            [package_venv.envconfig.envpython, "-c", script],
            returnout=True,
            action=action,
            cwd=session.config.setupdir,
        )
        report.verbosity2(result)
        return config.distdir.join(result.split("\n")[-2])


def get_build_requires(build_info, package_venv, session):
    with session.newaction(
        package_venv, "get-build-requires", package_venv.envconfig.envdir
    ) as action:
        script = textwrap.dedent(
            """
                import {}
                import json

                backend = {}
                for_build_requires = backend.get_requires_for_build_{}(None)
                print(json.dumps(for_build_requires))
                        """.format(
                build_info.backend_module, build_info.backend_object, "sdist"
            )
        ).strip()
        result = package_venv._pcall(
            [package_venv.envconfig.envpython, "-c", script],
            returnout=True,
            action=action,
            cwd=session.config.setupdir,
        )
        return json.loads(result.split("\n")[-2])
