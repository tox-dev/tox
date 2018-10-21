import py
from filelock import FileLock, Timeout

import tox
from .view import create_session_view
from .builder import build_package


@tox.hookimpl
def tox_package(session, venv):
    """Build an sdist at first call return that for all calls"""
    if not hasattr(session, "package"):
        session.package, session.dist = get_package(session)
    return session.package


def get_package(session):
    """"Perform the package operation"""
    config, report = session.config, session.report
    if config.skipsdist:
        report.info("skipping sdist step")
        return None
    lock_file = str(
        session.config.toxworkdir.join("{}.lock".format(session.config.isolated_build_env))
    )
    lock = FileLock(lock_file)
    try:
        try:
            lock.acquire(0.0001)
        except Timeout:
            report.verbosity0("lock file {} present, will block until released".format(lock_file))
            lock.acquire()
        package = acquire_package(config, report, session)
        session_package = create_session_view(package, config.temp_dir, report)
        return session_package, package
    finally:
        lock.release(force=True)


def acquire_package(config, report, session):
    """acquire a source distribution (either by loading a local file or triggering a build)"""
    if not config.option.sdistonly and (config.sdistsrc or config.option.installpkg):
        path = get_local_package(config, report, session)
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


def get_local_package(config, report, session):
    path = config.option.installpkg
    if not path:
        path = config.sdistsrc
    py_path = py.path.local(session._resolve_package(path))
    report.info("using package {!r}, skipping 'sdist' activity ".format(str(py_path)))
    return py_path
