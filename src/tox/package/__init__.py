from __future__ import absolute_import, unicode_literals

from collections import namedtuple

import py
import tox
from filelock import FileLock, Timeout
from .build import build_package
from .view import create_session_view

Package = namedtuple("Package", ["session_view", "dist"])


@tox.hookimpl
def tox_package(session, venv):
    """Build an sdist at first call return that for all calls"""
    if not hasattr(session, "package"):
        package = get_package(session)
        session.package = package
    return session.package


def get_package(session):
    """"Perform the package operation"""
    # there may be only one operation running out of this, ensure this
    lock_file = str(
        session.config.toxworkdir.join("{}.lock".format(session.config.isolated_build_env))
    )

    lock = FileLock(lock_file)
    try:
        try:
            lock.acquire(0.0001)
        except Timeout:
            session.report.verbosity0(
                "lock file {} present, will block until released".format(lock_file)
            )
            lock.acquire()
        package_path = acquire_package(session)
        if package_path is None:
            return None
        session_package_path = create_session_view(
            package_path, session.config.temp_dir, session.report
        )
        return Package(session_package_path, package_path)
    finally:
        lock.release(force=True)


def acquire_package(session):
    """acquire a source distribution (either by loading a local file or triggering a build)"""
    config = session.config
    if not config.option.sdistonly and (config.sdistsrc or config.option.installpkg):
        path = get_local_package(session)
    else:
        try:
            path = build_package(session)
        except tox.exception.InvocationError as exception:
            session.report.error("FAIL could not package project - v = {!r}".format(exception))
            return None
        sdist_file = config.distshare.join(path.basename)
        if sdist_file != path:
            session.report.info("copying new sdistfile to {!r}".format(str(sdist_file)))
            try:
                sdist_file.dirpath().ensure(dir=1)
            except py.error.Error:
                session.report.warning(
                    "could not copy distfile to {}".format(sdist_file.dirpath())
                )
            else:
                path.copy(sdist_file)
    return path


def get_local_package(session):
    path = session.config.option.installpkg
    if not path:
        path = session.config.sdistsrc
    py_path = py.path.local(session._resolve_package(path))
    session.report.info("using package {!r}, skipping 'sdist' activity ".format(str(py_path)))
    return py_path
