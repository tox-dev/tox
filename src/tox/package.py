import sys

import py

import tox


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
            path = make_sdist(report, config, session)
        except tox.exception.InvocationError:
            v = sys.exc_info()[1]
            report.error("FAIL could not package project - v = {!r}".format(v))
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


def make_sdist(report, config, session):
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
