import json
import sys
import textwrap
from collections import namedtuple

import pkg_resources
import py
import six
import toml

import tox
from tox.config import DepConfig
from tox.venv import CreationConfig

BuildInfo = namedtuple("BuildInfo", ["requires", "backend_module", "backend_object"])


@tox.hookimpl
def tox_package(session, venv):
    """Build an sdist at first call return that for all calls"""
    if not hasattr(session, "package"):
        session.package = get_package(session)
    return session.package


def get_package(session):
    """"Perform the package operation"""
    config, report = session.config, session.report
    if config.skipsdist:
        report.info("skipping sdist step")
        return None
    if not config.option.sdistonly and (config.sdistsrc or config.option.installpkg):
        path = config.option.installpkg
        if not path:
            path = config.sdistsrc
        path = session._resolve_package(path)
        report.info("using package {!r}, skipping 'sdist' activity ".format(str(path)))
    else:
        try:
            path = build_package(config, report, session)
        except tox.exception.InvocationError as exception:
            report.error("FAIL could not package project - v = {!r}".format(exception))
            return None
        sdist_file = config.distshare.join(path.basename)
        if sdist_file != path:
            report.info("copying new sdistfile to {!r}".format(str(sdist_file)))
            try:
                sdist_file.dirpath().ensure(dir=1)
            except py.error.Error:
                report.warning("could not copy distfile to {}".format(sdist_file.dirpath()))
            else:
                path.copy(sdist_file)
    return path


def build_package(config, report, session):
    if not config.isolated_build:
        return make_sdist_legacy(report, config, session)
    else:
        return build_isolated(config, report, session)


def make_sdist_legacy(report, config, session):
    setup = config.setupdir.join("setup.py")
    if not setup.check():
        report.error(
            "No setup.py file found. The expected location is:\n"
            "  {}\n"
            "You can\n"
            "  1. Create one:\n"
            "     https://packaging.python.org/tutorials/distributing-packages/#setup-py\n"
            "  2. Configure tox to avoid running sdist:\n"
            "     http://tox.readthedocs.io/en/latest/example/general.html"
            "#avoiding-expensive-sdist".format(setup)
        )
        raise SystemExit(1)
    with session.newaction(None, "packaging") as action:
        action.setactivity("sdist-make", setup)
        session.make_emptydir(config.distdir)
        action.popen(
            [sys.executable, setup, "sdist", "--formats=zip", "--dist-dir", config.distdir],
            cwd=config.setupdir,
        )
        try:
            return config.distdir.listdir()[0]
        except py.error.ENOENT:
            # check if empty or comment only
            data = []
            with open(str(setup)) as fp:
                for line in fp:
                    if line and line[0] == "#":
                        continue
                    data.append(line)
            if not "".join(data).strip():
                report.error("setup.py is empty")
                raise SystemExit(1)
            report.error(
                "No dist directory found. Please check setup.py, e.g with:\n"
                "     python setup.py sdist"
            )
            raise SystemExit(1)


def build_isolated(config, report, session):
    build_info = get_build_info(config.setupdir, report)
    package_venv = session.getvenv(config.isolated_build_package_env)
    package_venv.envconfig.deps_matches_subset = True

    package_venv.envconfig.deps = [DepConfig(r, None) for r in build_info.requires]
    toml_require = {pkg_resources.Requirement(r).key for r in build_info.requires}
    if not session.setupenv(package_venv):
        raise SystemExit(1)

    live_config = package_venv._getliveconfig()
    previous_config = CreationConfig.readconfig(package_venv.path_config)
    if not previous_config or not previous_config.matches(live_config, True):
        session.finishvenv(package_venv)

    build_requires = get_build_requires(build_info, package_venv, session)
    for requirement in build_requires:
        pkg_requirement = pkg_resources.Requirement(requirement)
        if pkg_requirement.key not in toml_require:
            package_venv.envconfig.deps.append(DepConfig(requirement, None))

    if not session.setupenv(package_venv):
        raise SystemExit(1)

    session.finishvenv(package_venv)
    return perform_isolated_build(build_info, package_venv, session, config)


def get_build_info(folder, report):
    toml_file = folder.join("pyproject.toml")

    # as per https://www.python.org/dev/peps/pep-0517/

    def abort(message):
        report.error("{} inside {}".format(message, toml_file))
        raise SystemExit(1)

    if not toml_file.exists():
        report.error("missing {}".format(toml_file))
        raise SystemExit(1)

    with open(str(toml_file)) as file_handler:
        config_data = toml.load(file_handler)

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


def perform_isolated_build(build_info, package_venv, session, config):
    with session.newaction(
        package_venv, "perform isolated build", package_venv.envconfig.envdir
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
        config.distdir.ensure_dir()
        result = action.popen([package_venv.envconfig.envpython, "-c", script], returnout=True)
        return config.distdir.join(result.split("\n")[-2])


def get_build_requires(build_info, package_venv, session):
    with session.newaction(
        package_venv, "get build requires", package_venv.envconfig.envdir
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
        result = action.popen([package_venv.envconfig.envpython, "-c", script], returnout=True)
        return json.loads(result.split("\n")[-2])
